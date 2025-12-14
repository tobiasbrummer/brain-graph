#!/usr/bin/env python3
"""
Chunker: Markdown → nodes.json + edges.json

Parst Markdown-Struktur, splittet Text in adaptive Chunks mit Overlap,
behandelt Codeblöcke atomar.

Usage:
    brain pipeline chunk input.md
    python -m brain_graph.pipeline.chunker -i input.md

Outputs (default):
    - `.brain_graph/data/nodes/<YYYY-MM>/*.nodes.json`
    - `.brain_graph/data/edges/<YYYY-MM>/*.edges.json`
    - `.brain_graph/data/meta/<YYYY-MM>/*.meta.json`
"""

import argparse
import hashlib
import json
import re
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import ulid
import pysbd
import xxhash
import mq as markdown_query  # External dependency
from langdetect import detect, LangDetectException

from brain_graph.utils.file_utils import (
    get_or_generate_ulid,
    get_output_paths,
    ensure_output_dirs,
    get_month_folder,
    slugify,
    get_source_hash,
    get_source_version
)
from brain_graph.utils.cli_utils import emit_json, error_result, ms_since, ok_result

# -----------------------------------------------------------------------------
# Config
# -----------------------------------------------------------------------------

def load_config(config_path: Path | None = None) -> dict[str, Any]:
    """
    Load chunking configuration.

    If `config_path` is not provided, searches for a config file in the current
    directory and parents in this order:
    1) `.brain_graph/config/config.json` (new structure)
    2) `config.json` (legacy fallback)

    For backwards compatibility, `chunking_*` keys are mapped to `chunk_*`.
    """
    defaults = {
        "chunk_target_tokens": 384,
        "chunk_min_tokens": 100,
        "chunk_overlap_tokens": 50,
        "chunk_language": "de",
    }

    if config_path is None:
        for parent in [Path.cwd(), *Path.cwd().parents]:
            candidate = parent / ".brain_graph" / "config" / "config.json"
            if candidate.exists():
                config_path = candidate
                break
            candidate = parent / "config.json"
            if candidate.exists():
                config_path = candidate
                break

    if config_path and config_path.exists():
        user_config = json.loads(config_path.read_text(encoding="utf-8"))
        # Map chunking_ prefix to chunk_ for backwards compatibility
        mapped_config = {}
        for key, value in user_config.items():
            if key.startswith("chunking_"):
                mapped_key = key.replace("chunking_", "chunk_")
                mapped_config[mapped_key] = value
            elif key.startswith("chunk_"):
                mapped_config[key] = value
        defaults.update(mapped_config)

    return defaults


# -----------------------------------------------------------------------------
# ULID Generation
# -----------------------------------------------------------------------------

def _ulid_timestamp_bytes(ulid_str: str) -> bytes:
    """Return the 6 timestamp bytes from a ULID string."""
    return ulid.from_str(ulid_str).bytes[:6]


def make_ulid(seed: str, *, ts_bytes: bytes) -> str:
    """Deterministische ULID aus Seed + Timestamp-Bytes (ULID time-part)."""
    digest = hashlib.sha1(seed.encode("utf-8")).digest()
    return str(ulid.from_bytes(ts_bytes + digest[:10]))


# -----------------------------------------------------------------------------
# Markdown Parsing
# -----------------------------------------------------------------------------

@dataclass
class Block:
    """Ein Block aus dem Markdown."""
    type: str  # "heading", "code", "text"
    content: str
    level: int = 0  # Heading-Level (1-6)
    language: str = ""  # Code-Sprache
    char_start: int = 0
    char_end: int = 0


HEADING_RE = re.compile(r"^(#{1,6})\s+(.+)$")


@dataclass
class Marker:
    """Ein Strukturmarker im Markdown."""
    type: str  # "heading", "code"
    start: int
    end: int
    content: str
    level: int = 0
    language: str = ""


def parse_markdown(text: str) -> list[Block]:
    """
    Parst Markdown in Blöcke.
    
    Strategie:
    1. Headings und Code-Blöcke als Marker mit Position extrahieren
    2. Nach Position sortieren
    3. Text zwischen Markern als Content-Blöcke
    """
    markers: list[Marker] = []
    
    # Headings extrahieren
    headings = markdown_query.run("select(.h)", text, None)
    for item in headings:
        if not item.text or not item.text.strip():
            continue
        
        pos = text.find(item.text)
        if pos == -1:
            continue
        
        match = HEADING_RE.match(item.text)
        if match:
            level = len(match.group(1))
            title = match.group(2).strip()
        else:
            level = item.text.count("#", 0, 7)
            title = item.text.lstrip("#").strip()
        
        markers.append(Marker(
            type="heading",
            start=pos,
            end=pos + len(item.text),
            content=title,
            level=level,
        ))
    
    # Code-Blöcke extrahieren
    codes = markdown_query.run("select(.code)", text, None)
    for item in codes:
        if not item.text or not item.text.strip():
            continue
        
        pos = text.find(item.text)
        if pos == -1:
            continue
        
        lines = item.text.split("\n")
        first_line = lines[0] if lines else ""
        lang = first_line.replace("`", "").strip()
        
        # Code ohne Fences
        code_lines = lines[1:-1] if len(lines) > 2 else lines[1:] if len(lines) > 1 else []
        code_content = "\n".join(code_lines)
        
        markers.append(Marker(
            type="code",
            start=pos,
            end=pos + len(item.text),
            content=code_content,
            language=lang,
        ))
    
    # Nach Position sortieren
    markers.sort(key=lambda m: m.start)
    
    # Blöcke generieren
    blocks: list[Block] = []
    last_end = 0
    
    for marker in markers:
        # Text vor diesem Marker?
        if marker.start > last_end:
            text_content = text[last_end:marker.start]
            if text_content.strip():
                blocks.append(Block(
                    type="text",
                    content=text_content,
                    char_start=last_end,
                    char_end=marker.start,
                ))
        
        # Marker selbst
        if marker.type == "heading":
            blocks.append(Block(
                type="heading",
                content=marker.content,
                level=marker.level,
                char_start=marker.start,
                char_end=marker.end,
            ))
        elif marker.type == "code":
            blocks.append(Block(
                type="code",
                content=marker.content,
                language=marker.language,
                char_start=marker.start,
                char_end=marker.end,
            ))
        
        last_end = marker.end
    
    # Text nach letztem Marker
    if last_end < len(text):
        text_content = text[last_end:]
        if text_content.strip():
            blocks.append(Block(
                type="text",
                content=text_content,
                char_start=last_end,
                char_end=len(text),
            ))
    
    return blocks


# -----------------------------------------------------------------------------
# Sentence Splitting & Chunking
# -----------------------------------------------------------------------------

def estimate_tokens(text: str) -> int:
    """Grobe Token-Schätzung (chars / 4)."""
    return len(text) // 4


def detect_language(text: str, default: str = "en") -> str:
    """
    Erkennt Sprache eines Textes.

    Returns: ISO 639-1 code ('de', 'en', etc.) oder default bei Fehler
    """
    if not text or len(text) < 20:
        return default

    try:
        # Nutze ersten 500 chars für Detection
        sample = text[:500]
        lang = detect(sample)
        return lang
    except LangDetectException:
        return default


def split_sentences(text: str, segmenter: pysbd.Segmenter) -> list[tuple[str, int, int]]:
    """Splittet Text in Sätze mit Positionen.

    Returns: Liste von (sentence, char_start, char_end)
    """
    sentences = segmenter.segment(text)
    result = []
    pos = 0

    for sent in sentences:
        sent = sent.strip()
        if not sent:
            continue

        # Finde Satz im Text
        idx = text.find(sent, pos)
        if idx == -1:
            # Fallback: schätze Position
            idx = pos

        result.append((sent, idx, idx + len(sent)))
        pos = idx + len(sent)

    return result


def split_long_sentence(
    text: str,
    char_start: int,
    target_tokens: int
) -> list[tuple[str, int, int]]:
    """Splittet einen zu langen Satz an Kommas, Semikola, etc."""
    if estimate_tokens(text) <= target_tokens:
        return [(text, char_start, char_start + len(text))]

    import re
    # Split an Kommas, Semikola, etc.
    split_pattern = r'([,;:\-–—]\s+)'
    segments = re.split(split_pattern, text)

    parts = []
    current_part = ""
    current_start = char_start

    for segment in segments:
        # Probe: würde das Hinzufügen dieses Segments zu groß?
        test_part = current_part + segment
        test_tokens = estimate_tokens(test_part)

        if test_tokens > target_tokens and current_part:
            # Aktuellen Part speichern
            stripped = current_part.strip()
            if stripped:
                parts.append((stripped, current_start, current_start + len(stripped)))
                current_start += len(current_part)
            current_part = segment
        else:
            current_part += segment

    # Rest
    stripped = current_part.strip()
    if stripped:
        parts.append((stripped, current_start, current_start + len(stripped)))

    # Wenn immer noch zu große Teile, hard split
    final_parts = []
    max_chars = target_tokens * 4
    for part_text, part_start, part_end in parts:
        if estimate_tokens(part_text) > target_tokens:
            # Hard split
            for i in range(0, len(part_text), max_chars):
                chunk = part_text[i:i+max_chars].strip()
                if chunk:
                    final_parts.append((chunk, part_start + i, part_start + i + len(chunk)))
        else:
            final_parts.append((part_text, part_start, part_end))

    return final_parts if final_parts else [(text, char_start, char_start + len(text))]


def create_adaptive_chunks(
    sentences: list[tuple[str, int, int]],
    target_tokens: int,
    min_tokens: int,
    overlap_tokens: int,
) -> list[tuple[str, int, int, int]]:
    """
    Gruppiert Sätze in Chunks mit adaptiver Größe und Overlap.

    Args:
        sentences: Liste von (text, char_start, char_end)

    Returns: Liste von (chunk_text, chunk_start, chunk_end, overlap_chars)
    """
    if not sentences:
        return []

    chunks: list[tuple[str, int, int, int]] = []
    current_sents: list[tuple[str, int, int]] = []
    current_tokens = 0

    # Splitten von zu langen Sätzen
    processed_sentences = []
    for sent_text, sent_start, sent_end in sentences:
        sent_tokens = estimate_tokens(sent_text)

        # Wenn Satz zu lang, weiter splitten
        if sent_tokens > target_tokens:
            sub_parts = split_long_sentence(sent_text, sent_start, target_tokens)
            processed_sentences.extend(sub_parts)
        else:
            processed_sentences.append((sent_text, sent_start, sent_end))

    for sent_text, sent_start, sent_end in processed_sentences:
        sent_tokens = estimate_tokens(sent_text)

        # Passt der Satz noch rein?
        if current_tokens + sent_tokens <= target_tokens:
            current_sents.append((sent_text, sent_start, sent_end))
            current_tokens += sent_tokens
        else:
            # Chunk ist voll - speichern
            if current_sents:
                texts = [s[0] for s in current_sents]
                chunk_text = " ".join(texts)
                chunk_start = current_sents[0][1]
                chunk_end = current_sents[-1][2]

                # Overlap berechnen
                overlap_chars = 0
                if chunks:
                    overlap_sents = []
                    overlap_tok = 0
                    for s in reversed(current_sents):
                        s_tok = estimate_tokens(s[0])
                        if overlap_tok + s_tok > overlap_tokens:
                            break
                        overlap_sents.insert(0, s)
                        overlap_tok += s_tok
                    overlap_chars = sum(len(s[0]) for s in overlap_sents)

                chunks.append((chunk_text, chunk_start, chunk_end, overlap_chars))

                # Starte neuen Chunk mit Overlap
                overlap_sents = []
                overlap_tok = 0
                for s in reversed(current_sents):
                    s_tok = estimate_tokens(s[0])
                    if overlap_tok + s_tok > overlap_tokens:
                        break
                    overlap_sents.insert(0, s)
                    overlap_tok += s_tok

                current_sents = overlap_sents
                current_tokens = overlap_tok

            # Aktueller Satz zum neuen Chunk
            current_sents.append((sent_text, sent_start, sent_end))
            current_tokens += sent_tokens

    # Rest-Chunk
    if current_sents:
        texts = [s[0] for s in current_sents]
        chunk_text = " ".join(texts)
        chunk_start = current_sents[0][1]
        chunk_end = current_sents[-1][2]

        remaining_tokens = estimate_tokens(chunk_text)

        # Wenn zu klein, merge mit vorigem Chunk
        if remaining_tokens < min_tokens and chunks:
            prev_text, prev_start, prev_end, prev_overlap = chunks.pop()
            chunk_text = prev_text + " " + chunk_text
            chunk_start = prev_start
            chunks.append((chunk_text, chunk_start, chunk_end, prev_overlap))
        else:
            overlap_chars = 0
            if chunks:
                overlap_sents = []
                overlap_tok = 0
                for s in reversed(current_sents):
                    s_tok = estimate_tokens(s[0])
                    if overlap_tok + s_tok > overlap_tokens:
                        break
                    overlap_sents.insert(0, s)
                    overlap_tok += s_tok
                overlap_chars = sum(len(s[0]) for s in overlap_sents)
            chunks.append((chunk_text, chunk_start, chunk_end, overlap_chars))

    return chunks


# -----------------------------------------------------------------------------
# Graph Building
# -----------------------------------------------------------------------------

# Sections die beim Chunking übersprungen werden (meist nur Link-Listen)
SKIP_SECTIONS = {
    "siehe auch",
    "weblinks",
    "einzelnachweise",
    "literatur",
    "quellen",
    "external links",
    "references",
    "see also",
    "bibliography",
    "further reading",
    "nachschlagewerke",
    "diskografien",
}


@dataclass
class Node:
    id: str
    ulid: str
    type: str  # "section", "chunk", "code"
    content: str
    title: str = ""
    level: int = 0
    language: str = ""
    char_start: int = 0
    char_end: int = 0
    
    def to_dict(self) -> dict:
        d = {
            "id": self.id,
            "ulid": self.ulid,
            "type": self.type,
        }
        if self.title:
            d["title"] = self.title
        if self.type == "section":
            d["level"] = self.level
        if self.type in ("chunk", "code") and self.language:
            d["language"] = self.language
        if self.type in ("chunk", "code"):
            d["char_start"] = self.char_start
            d["char_end"] = self.char_end
        return d


@dataclass
class Edge:
    from_id: str
    to_id: str
    type: str  # "parent_of", "contains", "next"
    weight: int = 10
    overlap_chars: int = 0
    
    def to_dict(self) -> dict:
        d = {
            "from": self.from_id,
            "to": self.to_id,
            "type": self.type,
        }
        if self.type == "next":
            if self.overlap_chars > 0:
                d["overlap_chars"] = self.overlap_chars
        else:
            d["weight"] = self.weight
        return d


def build_graph(
    blocks: list[Block],
    source_file: str,
    config: dict[str, Any],
    *,
    doc_ulid: str,
) -> tuple[list[Node], list[Edge]]:
    """Baut Nodes und Edges aus Blöcken."""
    nodes: list[Node] = []
    edges: list[Edge] = []

    ts_bytes = _ulid_timestamp_bytes(doc_ulid)

    # Section-Stack für Hierarchie
    section_stack: list[Node] = []
    current_section: Node | None = None

    # Skip-Tracking: ob wir in einer zu überspringenden Section sind
    skip_until_level: int | None = None

    # Chunk-Sequenz für next-Edges
    prev_chunk: Node | None = None
    chunk_counter = 0

    # Segmenter-Cache für verschiedene Sprachen
    segmenter_cache: dict[str, pysbd.Segmenter] = {}

    def get_segmenter(lang: str) -> pysbd.Segmenter:
        """Holt oder erstellt Segmenter für Sprache."""
        if lang not in segmenter_cache:
            try:
                segmenter_cache[lang] = pysbd.Segmenter(language=lang, clean=False)
            except ValueError:
                # Fallback auf Deutsch wenn Sprache nicht unterstützt
                print(f"Warning: Language '{lang}' not supported by pysbd, falling back to 'de'", file=sys.stderr)
                segmenter_cache[lang] = pysbd.Segmenter(language="de", clean=False)
        return segmenter_cache[lang]
    
    def make_id(prefix: str, content: str) -> str:
        """Erstellt eine ID aus Prefix und Content-Hash (xxhash64)."""
        short_hash = xxhash.xxh64(content.encode()).hexdigest()[:8]
        return f"{prefix}_{short_hash}"
    
    for block in blocks:
        if block.type == "heading":
            # Prüfe ob wir eine Skip-Section beenden
            if skip_until_level is not None and block.level <= skip_until_level:
                skip_until_level = None

            # Prüfe ob dies eine zu überspringende Section ist
            title_lower = block.content.lower().strip()
            if title_lower in SKIP_SECTIONS:
                skip_until_level = block.level
                print(f"Skipping section: {block.content}", file=sys.stderr)

            # Section Node
            node_id = make_id("sec", f"{source_file}:{block.content}")
            node = Node(
                id=node_id,
                ulid=make_ulid(node_id, ts_bytes=ts_bytes),
                type="section",
                content=block.content,
                title=block.content,
                level=block.level,
                char_start=block.char_start,
                char_end=block.char_end,
            )
            nodes.append(node)

            # Parent-Edge zur übergeordneten Section
            while section_stack and section_stack[-1].level >= block.level:
                section_stack.pop()

            if section_stack:
                edges.append(Edge(
                    from_id=section_stack[-1].id,
                    to_id=node.id,
                    type="parent_of",
                    weight=10,
                ))

            section_stack.append(node)
            current_section = node
        
        elif block.type == "code":
            # Skip wenn in übersprungener Section
            if skip_until_level is not None:
                continue

            # Code Node (atomar)
            node_id = make_id("code", f"{source_file}:{block.char_start}:{block.content[:50]}")
            node = Node(
                id=node_id,
                ulid=make_ulid(node_id, ts_bytes=ts_bytes),
                type="code",
                content=block.content,
                language=block.language,
                char_start=block.char_start,
                char_end=block.char_end,
            )
            nodes.append(node)

            # Contains-Edge von aktueller Section
            if current_section:
                edges.append(Edge(
                    from_id=current_section.id,
                    to_id=node.id,
                    type="contains",
                    weight=8,
                ))

            # Next-Edge vom vorherigen Chunk
            if prev_chunk:
                edges.append(Edge(
                    from_id=prev_chunk.id,
                    to_id=node.id,
                    type="next",
                ))
            prev_chunk = node

        elif block.type == "text":
            # Skip wenn in übersprungener Section
            if skip_until_level is not None:
                continue

            # Text → Sätze → Chunks
            # Erkenne Sprache für diesen Block
            block_lang = detect_language(block.content, default=config.get("chunk_language", "en"))
            block_segmenter = get_segmenter(block_lang)

            sentences = split_sentences(block.content, block_segmenter)
            chunks = create_adaptive_chunks(
                sentences,
                target_tokens=config["chunk_target_tokens"],
                min_tokens=config["chunk_min_tokens"],
                overlap_tokens=config["chunk_overlap_tokens"],
            )

            for idx, (chunk_text, chunk_start, chunk_end, overlap_chars) in enumerate(chunks):
                # Erster Chunk nach einer Section: char_start bei Überschrift beginnen
                if idx == 0 and current_section:
                    # Inklusive Überschrift
                    actual_char_start = current_section.char_start
                else:
                    actual_char_start = block.char_start + chunk_start

                chunk_counter += 1
                node_id = make_id("chunk", f"{source_file}:{chunk_counter}:{chunk_text[:50]}")
                node = Node(
                    id=node_id,
                    ulid=make_ulid(node_id, ts_bytes=ts_bytes),
                    type="chunk",
                    content=chunk_text,
                    language=block_lang,
                    char_start=actual_char_start,
                    char_end=block.char_start + chunk_end,
                )
                nodes.append(node)
                
                # Contains-Edge von aktueller Section
                if current_section:
                    edges.append(Edge(
                        from_id=current_section.id,
                        to_id=node.id,
                        type="contains",
                        weight=8,
                    ))
                
                # Next-Edge vom vorherigen Chunk
                if prev_chunk:
                    edges.append(Edge(
                        from_id=prev_chunk.id,
                        to_id=node.id,
                        type="next",
                        overlap_chars=overlap_chars,
                    ))
                prev_chunk = node
    
    return nodes, edges


# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------

def main():
    start = time.perf_counter()
    parser = argparse.ArgumentParser(description="Chunk Markdown to graph")
    parser.add_argument("-i", "--input", type=Path, required=True, help="Input Markdown file")
    parser.add_argument("-c", "--config", type=Path, help="config.json path")
    parser.add_argument("--base-dir", type=Path, default=Path(".brain_graph/data"),
                        help="Base output directory (default: .brain_graph/data)")
    parser.add_argument("--vault-dir", type=Path, default=Path("vault"),
                        help="Vault directory for permanent storage (default: vault)")
    parser.add_argument("--delete-source", action="store_true",
                        help="Delete source file after processing (default: keep)")
    parser.add_argument("--force", action="store_true",
                        help="Force processing even if vault file unchanged")
    parser.add_argument(
        "--format",
        choices=["json", "text"],
        default="json",
        help="Output format (default: json)",
    )
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output")
    parser.add_argument("--debug", action="store_true", help="Include traceback in JSON error output")
    args = parser.parse_args()

    try:
        if not args.input.exists():
            raise FileNotFoundError(f"File not found: {args.input}")

        # Config laden
        config = load_config(args.config)

        # Markdown parsen
        text = args.input.read_text(encoding="utf-8")
        had_ulid = bool(re.search(r"\+id:[A-Z0-9]{26}", text))

        # ULID generieren/extrahieren und in MD injizieren
        doc_ulid = get_or_generate_ulid(args.input, text)
        print(f"Document ULID: {doc_ulid}", file=sys.stderr)

        # Monat aus Input-Pfad nutzen (falls vault/YYYY-MM/) oder aktuellen Monat
        parent_name = args.input.parent.name
        if re.match(r'^\d{4}-\d{2}$', parent_name):
            month = parent_name
        else:
            month = get_month_folder()

        # ULID-Suffix aus stem entfernen (falls Reprocessing von vault-Datei)
        stem = re.sub(r'-[A-Z0-9]{6}$', '', args.input.stem, flags=re.IGNORECASE)
        slug = slugify(stem)
        ulid_suffix = doc_ulid[-6:]
        vault_filename = f"{slug}-{ulid_suffix}.md"
        vault_path = args.vault_dir / month / vault_filename

        # Vault-Verzeichnis erstellen
        vault_path.parent.mkdir(parents=True, exist_ok=True)

        # Skip-Logik: Wenn vault existiert und hash gleich
        vault_unchanged = False
        input_is_vault_target = False
        try:
            input_is_vault_target = args.input.resolve() == vault_path.resolve()
        except OSError:
            # Fallback for non-resolvable paths (should be rare since input exists)
            input_is_vault_target = args.input.absolute() == vault_path.absolute()

        if input_is_vault_target:
            print("✓ Input already at vault path, skipping copy", file=sys.stderr)
            vault_unchanged = True
        elif vault_path.exists() and not args.force:
            vault_hash = get_source_hash(vault_path)
            input_hash = get_source_hash(args.input)

            if vault_hash == input_hash:
                print("✓ Vault file unchanged, skipping copy", file=sys.stderr)
                vault_unchanged = True
            else:
                print("✎ Vault file changed, updating...", file=sys.stderr)

        copied_to_vault = (not vault_unchanged) and (not input_is_vault_target)
        # Datei nach vault kopieren (mit aktualisierter ULID)
        if copied_to_vault:
            import shutil
            try:
                shutil.copy2(args.input, vault_path)
                print(f"Copied to vault: {vault_path}", file=sys.stderr)
            except shutil.SameFileError:
                copied_to_vault = False
                print("✓ Input already at vault path, skipping copy", file=sys.stderr)

        deleted_source = False
        # Optional: Originaldatei löschen
        if args.delete_source:
            if input_is_vault_target:
                print("Warning: --delete-source ignored (input is already in vault)", file=sys.stderr)
            else:
                args.input.unlink()
                deleted_source = True
                print(f"Deleted source: {args.input}", file=sys.stderr)

        # Ab jetzt mit vault-Datei arbeiten
        working_file = vault_path
        text = working_file.read_text(encoding="utf-8")

        # Output-Pfade basierend auf vault-Datei generieren
        output_paths = get_output_paths(working_file, doc_ulid, args.base_dir)
        ensure_output_dirs(output_paths)

        # Blocks parsen
        blocks = parse_markdown(text)
        print(f"Parsed {len(blocks)} blocks", file=sys.stderr)

        # Graph bauen (mit automatischer Spracherkennung pro Block)
        nodes, edges = build_graph(blocks, working_file.name, config, doc_ulid=doc_ulid)

        # Nodes und Edges mit leeren Feldern für spätere Schritte erweitern
        nodes_data = []
        for n in nodes:
            node_dict = n.to_dict()
            # Füge leere Felder hinzu, die von späteren Schritten gefüllt werden
            if n.type == "chunk":
                node_dict.setdefault("summary", None)
                node_dict.setdefault("categories", [])
            nodes_data.append(node_dict)

        edges_data = [e.to_dict() for e in edges]

        # JSON schreiben
        output_paths['nodes'].write_text(
            json.dumps(nodes_data, ensure_ascii=False, indent=2),
            encoding='utf-8'
        )
        output_paths['edges'].write_text(
            json.dumps(edges_data, ensure_ascii=False, indent=2),
            encoding='utf-8'
        )

        # meta.json erstellen
        now = datetime.now(timezone.utc)

        # Source hash und git version
        source_hash = get_source_hash(vault_path)
        git_info = get_source_version(vault_path)

        meta = {
            "source_file": str(vault_path),  # Vault-Pfad als canonical source
            "original_source": str(args.input) if args.input != vault_path else None,
            "ulid": doc_ulid,
            "source_hash": source_hash,
            "source_commit": git_info["source_commit"],
            "source_commit_date": git_info["source_commit_date"],
            "source_dirty": git_info["source_dirty"],
            "created_at": now.isoformat(),
            "modified_at": now.isoformat(),
            "uses": 1,
            "importance": None,  # Wird von Taxonomie vererbt
            "decay": None,       # Wird von Taxonomie vererbt
            "categories": [],    # Wird von taxonomy_matcher gefüllt
            "processing_steps": [
                {
                    "step": "chunking",
                    "completed": True,
                    "timestamp": now.isoformat(),
                    "node_count": len(nodes),
                    "edge_count": len(edges)
                }
            ]
        }

        output_paths['meta'].write_text(
            json.dumps(meta, ensure_ascii=False, indent=2),
            encoding='utf-8'
        )

        # Stats
        node_types = {}
        for n in nodes:
            node_types[n.type] = node_types.get(n.type, 0) + 1

        edge_types = {}
        for e in edges:
            edge_types[e.type] = edge_types.get(e.type, 0) + 1

        print(f"Written {output_paths['nodes']} ({len(nodes)} nodes: {node_types})", file=sys.stderr)
        print(f"Written {output_paths['edges']} ({len(edges)} edges: {edge_types})", file=sys.stderr)
        print(f"Written {output_paths['meta']}", file=sys.stderr)

        result = ok_result(
            "chunker",
            input=str(args.input),
            doc_ulid=doc_ulid,
            id_was_in_source=had_ulid,
            copied_to_vault=copied_to_vault,
            deleted_source=deleted_source,
            vault_path=str(vault_path),
            output={
                "nodes": str(output_paths["nodes"]),
                "edges": str(output_paths["edges"]),
                "meta": str(output_paths["meta"]),
            },
            counts={
                "nodes": len(nodes),
                "edges": len(edges),
                "nodes_by_type": node_types,
                "edges_by_type": edge_types,
            },
            duration_ms=ms_since(start),
        )
        if args.format == "json":
            emit_json(result, pretty=args.pretty)
        return 0
    except Exception as e:
        if args.format == "json":
            emit_json(error_result("chunker", e, include_traceback=args.debug, duration_ms=ms_since(start)), pretty=args.pretty)
            return 1
        raise

if __name__ == "__main__":
    raise SystemExit(main())
