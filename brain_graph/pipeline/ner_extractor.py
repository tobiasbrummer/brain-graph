#!/usr/bin/env python3
"""
NER Extractor: Extrahiert Named Entities aus Chunks via spaCy.

Lädt Chunks, extrahiert Entities (Personen, Orte, Organisationen),
erstellt Entity-Nodes und Edges.

Usage:
    python ner_extractor.py -i vault/YYYY-MM/file.md
"""

import argparse
import hashlib
import json
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import spacy

from brain_graph.utils.file_utils import (
    extract_ulid_from_md,
    generate_ulid,
    get_output_paths,
    strip_ulid_lines,
    update_meta
)
from brain_graph.utils.cli_utils import emit_json, error_result, ms_since, ok_result


def detect_language(nodes: list[dict[str, Any]]) -> str:
    """Erkennt vorherrschende Sprache aus Chunks."""
    from collections import Counter

    languages = []
    for node in nodes:
        if node.get("type") == "chunk" and "language" in node:
            languages.append(node["language"])

    if not languages:
        return "de"  # Fallback

    # Häufigste Sprache
    most_common = Counter(languages).most_common(1)[0][0]
    return most_common


def load_spacy_model(lang: str = "de") -> spacy.Language:
    """Lädt spaCy-Modell für Sprache."""
    models = {
        "de": "de_core_news_lg",
        "en": "en_core_web_lg",
    }

    model_name = models.get(lang, "de_core_news_lg")

    try:
        return spacy.load(model_name)
    except OSError as e:
        raise RuntimeError(
            f"spaCy model '{model_name}' not found. Install with: python -m spacy download {model_name}"
        ) from e


def normalize_markdown(text: str) -> str:
    """Entfernt Markdown-Syntax vor NER."""
    import re
    text = strip_ulid_lines(text)
    # Links entfernen: [text](url) -> text
    text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)
    # Bold/Italic entfernen
    text = re.sub(r'\*\*([^\*]+)\*\*', r'\1', text)
    text = re.sub(r'\*([^\*]+)\*', r'\1', text)
    text = re.sub(r'__([^_]+)__', r'\1', text)
    text = re.sub(r'_([^_]+)_', r'\1', text)
    # Headers entfernen
    text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)
    # Code backticks entfernen
    text = re.sub(r'`([^`]+)`', r'\1', text)
    return text


def extract_chunk_text(
    chunk_node: dict[str, Any],
    source_text: str
) -> str:
    """Extrahiert und normalisiert Text aus Chunk."""
    start = chunk_node.get("char_start", 0)
    end = chunk_node.get("char_end", 0)
    text = source_text[start:end].strip()
    return normalize_markdown(text)


def make_entity_id(entity_text: str, entity_type: str) -> str:
    """Erstellt eindeutige ID für Entity.

    Nutzt nur den Text (nicht den Type) um Duplikate zu vermeiden.
    Z.B. "Linux" kann als GPE, PERSON oder ORG erkannt werden,
    soll aber nur eine Entity sein.
    """
    content = entity_text.lower()
    short_hash = hashlib.sha1(content.encode()).hexdigest()[:8]
    return f"entity_{short_hash}"


def extract_entities(
    text: str,
    nlp: spacy.Language,
    min_count: int = 1
) -> list[tuple[str, str]]:
    """Extrahiert Named Entities aus Text.

    Returns: [(entity_text, entity_type), ...]
    """
    import re

    doc = nlp(text)

    # Sammle Entities mit Typ
    entities = []
    for ent in doc.ents:
        # Filtere irrelevante Entity-Types
        if ent.label_ in ["MISC", "CARDINAL", "ORDINAL", "QUANTITY"]:
            continue

        # Normalisiere Text
        entity_text = ent.text.strip()

        # Filtere zu kurze Entities
        if len(entity_text) < 3:
            continue

        # Filtere URL-Artefakte und Markdown-Reste
        if any(char in entity_text for char in ['[', ']', '(', ')', '%', '{']):
            continue

        # Nur Entities mit Großbuchstaben am Anfang
        if not entity_text[0].isupper():
            continue

        # Filtere reine Akronyme (außer bekannte)
        known_acronyms = {"IBM", "BSD", "GNU", "MIT", "NASA", "CERN", "UNIX"}
        if entity_text.isupper() and len(entity_text) <= 4:
            if entity_text not in known_acronyms:
                continue

        # Filtere zu generische Wörter und Tech-Begriffe
        generic_terms = [
            # Deutsch
            'intensiv', 'staaten', 'kommission',
            'ki', 'al', 'black box', 'ki-systemen',
            'ai-alignment', 'ki-ausrichtung', 'sprachzeichen',
            'gpt-3', 'ki-verordnung',
            # English
            'cpu', 'gui', 'ram', 'usb', 'api', 'os',
        ]
        if entity_text.lower() in generic_terms:
            continue

        # Filtere einzelne Vornamen (nur bei PER)
        if ent.label_ == "PER" and len(entity_text.split()) == 1:
            # Erlaube nur bekannte Einzelnamen (z.B. "Turing", "Microsoft")
            if entity_text not in ["Turing"]:
                continue

        entities.append((entity_text, ent.label_))

    return entities


def process_chunks(
    nodes: list[dict[str, Any]],
    source_text: str,
    nlp: spacy.Language,
    min_occurrences: int = 2
) -> tuple[dict[str, dict[str, Any]], dict[str, list[str]]]:
    """Verarbeitet alle Chunks und extrahiert Entities.

    Returns: (entities_dict, chunk_to_entities_map)
        entities_dict: {entity_id: {text, type, count, chunks}}
        chunk_to_entities_map: {chunk_id: [entity_ids]}
    """
    entities = defaultdict(lambda: {
        "text": "",
        "type": "",
        "count": 0,
        "chunks": set()
    })

    chunk_to_entities = defaultdict(list)

    chunk_count = 0
    for node in nodes:
        if node.get("type") != "chunk":
            continue

        chunk_count += 1
        chunk_id = node["id"]

        # Extrahiere Text
        text = extract_chunk_text(node, source_text)
        if not text:
            continue

        # Extrahiere Entities
        print(f"Processing chunk {chunk_count}: {chunk_id}", file=sys.stderr)
        chunk_entities = extract_entities(text, nlp)

        for entity_text, entity_type in chunk_entities:
            entity_id = make_entity_id(entity_text, entity_type)

            # Aktualisiere Entity-Daten
            if not entities[entity_id]["text"]:
                entities[entity_id]["text"] = entity_text
                entities[entity_id]["type"] = entity_type

            entities[entity_id]["count"] += 1
            entities[entity_id]["chunks"].add(chunk_id)

            # Füge zu Chunk-Mapping hinzu
            if entity_id not in chunk_to_entities[chunk_id]:
                chunk_to_entities[chunk_id].append(entity_id)

    # Filtere Entities nach Mindest-Vorkommen
    filtered_entities = {
        eid: data for eid, data in entities.items()
        if data["count"] >= min_occurrences
    }

    # Aktualisiere Chunk-Mappings
    filtered_chunk_to_entities = {}
    for chunk_id, entity_ids in chunk_to_entities.items():
        filtered_ids = [eid for eid in entity_ids if eid in filtered_entities]
        if filtered_ids:
            filtered_chunk_to_entities[chunk_id] = filtered_ids

    return filtered_entities, filtered_chunk_to_entities


def create_entity_nodes(
    entities: dict[str, dict[str, Any]]
) -> list[dict[str, Any]]:
    """Erstellt Entity-Nodes."""
    nodes = []

    for entity_id, data in entities.items():
        # Konvertiere chunks set zu list für JSON
        chunk_list = sorted(data["chunks"])

        node = {
            "id": entity_id,
            "ulid": generate_ulid(entity_id),
            "type": "entity",
            "entity_type": data["type"],
            "text": data["text"],
            "occurrences": data["count"],
            "mentioned_in": chunk_list,
        }
        nodes.append(node)

    return nodes


def create_entity_edges(
    chunk_to_entities: dict[str, list[str]]
) -> list[dict[str, Any]]:
    """Erstellt Edges von Chunks zu Entities."""
    edges = []

    for chunk_id, entity_ids in chunk_to_entities.items():
        for entity_id in entity_ids:
            edge = {
                "from": chunk_id,
                "to": entity_id,
                "type": "mentions",
                "weight": 1,
            }
            edges.append(edge)

    return edges


def print_statistics(
    entities: dict[str, dict[str, Any]],
    chunk_to_entities: dict[str, list[str]]
):
    """Gibt Statistiken aus."""
    # Entity-Typen
    type_counts = Counter(data["type"] for data in entities.values())

    print("\n=== Statistics ===", file=sys.stderr)
    print(f"Total entities: {len(entities)}", file=sys.stderr)
    print(f"Chunks with entities: {len(chunk_to_entities)}", file=sys.stderr)
    print(f"\nEntity types:", file=sys.stderr)
    for etype, count in type_counts.most_common():
        print(f"  {etype}: {count}", file=sys.stderr)

    # Top Entities
    print(f"\nTop 10 entities by occurrence:", file=sys.stderr)
    top_entities = sorted(
        entities.items(),
        key=lambda x: x[1]["count"],
        reverse=True
    )[:10]

    for entity_id, data in top_entities:
        print(f"  {data['text']} ({data['type']}): {data['count']}x", file=sys.stderr)


def main():
    start = time.perf_counter()
    parser = argparse.ArgumentParser(description="Extract named entities from chunks")
    parser.add_argument("-i", "--input", type=Path, required=True, help="Source Markdown file")
    parser.add_argument("--base-dir", type=Path, default=Path(".brain_graph/data"),
                        help="Base data directory")
    parser.add_argument("-l", "--lang", default=None, choices=["de", "en"],
                        help="Language for spaCy model (auto-detected if not specified)")
    parser.add_argument("--min-occurrences", type=int, default=4,
                        help="Minimum occurrences for entity to be included")
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
            raise FileNotFoundError(f"Source file not found: {args.input}")

        # ULID extrahieren
        doc_ulid = extract_ulid_from_md(args.input)
        if not doc_ulid:
            raise ValueError(f"No ULID found in {args.input}")

        # Pfade ermitteln
        output_paths = get_output_paths(args.input, doc_ulid, args.base_dir)

        if not output_paths['nodes'].exists():
            raise FileNotFoundError(f"Nodes file not found: {output_paths['nodes']} (run chunker.py first)")

        # Lade Daten
        print("Loading nodes and source...", file=sys.stderr)
        nodes = json.loads(output_paths['nodes'].read_text(encoding="utf-8"))
        source_text = args.input.read_text(encoding="utf-8")

        # Auto-detect Sprache falls nicht angegeben
        lang = args.lang
        if lang is None:
            lang = detect_language(nodes)
            print(f"Auto-detected language: {lang}", file=sys.stderr)

        # Lade spaCy-Modell
        print(f"Loading spaCy model for '{lang}'...", file=sys.stderr)
        nlp = load_spacy_model(lang)

        chunk_count = sum(1 for n in nodes if n.get("type") == "chunk")
        print(f"Loaded {len(nodes)} nodes ({chunk_count} chunks)", file=sys.stderr)

        # Extrahiere Entities
        print("Extracting entities...", file=sys.stderr)
        entities, chunk_to_entities = process_chunks(
            nodes,
            source_text,
            nlp,
            args.min_occurrences
        )

        # Statistiken
        print_statistics(entities, chunk_to_entities)

        # Erstelle Nodes und Edges
        entity_nodes = create_entity_nodes(entities)
        entity_edges = create_entity_edges(chunk_to_entities)

        print(f"\nCreated {len(entity_nodes)} entity nodes", file=sys.stderr)
        print(f"Created {len(entity_edges)} entity edges", file=sys.stderr)

        # NER-Verzeichnisse erstellen
        output_paths['ner_nodes'].parent.mkdir(parents=True, exist_ok=True)
        output_paths['ner_edges'].parent.mkdir(parents=True, exist_ok=True)

        # NER-Files schreiben
        output_paths['ner_nodes'].write_text(
            json.dumps(entity_nodes, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        output_paths['ner_edges'].write_text(
            json.dumps(entity_edges, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )

        print(f"\nWritten {output_paths['ner_nodes']}", file=sys.stderr)
        print(f"Written {output_paths['ner_edges']}", file=sys.stderr)

        # Update meta.json
        update_meta(output_paths['meta'], {
            "step": "ner_extraction",
            "entity_count": len(entity_nodes),
            "edge_count": len(entity_edges),
            "language": lang,
            "min_occurrences": args.min_occurrences,
        })
        print(f"Updated {output_paths['meta']}", file=sys.stderr)

        result = ok_result(
            "ner_extractor",
            input=str(args.input),
            doc_ulid=doc_ulid,
            output={
                "ner_nodes": str(output_paths["ner_nodes"]),
                "ner_edges": str(output_paths["ner_edges"]),
                "meta": str(output_paths["meta"]),
            },
            counts={"entities": len(entity_nodes), "edges": len(entity_edges), "chunks": chunk_count},
            language=lang,
            min_occurrences=args.min_occurrences,
            duration_ms=ms_since(start),
        )
        if args.format == "json":
            emit_json(result, pretty=args.pretty)
        return 0
    except Exception as e:
        if args.format == "json":
            emit_json(error_result("ner_extractor", e, include_traceback=args.debug, duration_ms=ms_since(start)), pretty=args.pretty)
            return 1
        raise


if __name__ == "__main__":
    raise SystemExit(main())
