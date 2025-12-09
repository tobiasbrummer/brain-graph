#!/usr/bin/env python3
"""
Konvertiert den Kategorien-Teil aus taxonomy.md in zwei JSON-Strukturen:
- nodes.json: Flache Liste aller Kategorien mit id, ulid, Metadaten
- edges.json: Flache Liste aller Beziehungen (parent_of, related)

ID entspricht dem +name-Slug. ULIDs nur in Nodes (Normalisierung).
"""

import argparse
import hashlib
import json
import pathlib
import re
import datetime
from typing import List, Dict, Any, Optional

import ulid

HEADER_RE = re.compile(r"^(#+)\s+(.*)$")
FIELD_RE = re.compile(r"^\+([^:]+):(.*)$")


def parse_file(text: str) -> List[Dict[str, Any]]:
    """Parse markdown into raw node list with paths and fields."""
    nodes = []
    path: List[str] = []
    in_categories = False
    
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not in_categories:
            if line.startswith("## Kategorien"):
                in_categories = True
            continue
        if not line or line.startswith("---"):
            continue
            
        m = HEADER_RE.match(line)
        if m:
            level = len(m.group(1))  # ### => 3
            title = m.group(2).strip()
            slug = title.lower().replace(" ", "_")
            depth = level - 2  # ### -> 1
            path = path[: max(depth - 1, 0)] if depth > 0 else []
            path.append(slug)
            nodes.append({
                "path": list(path),
                "level": depth,
                "title": title,
                "fields": {}
            })
            continue
            
        m = FIELD_RE.match(line)
        if m and nodes:
            key = m.group(1).strip()
            val = m.group(2).strip()
            nodes[-1]["fields"][key] = val
            
    return nodes


def parse_keywords(val: str) -> List[str]:
    return [w.strip() for w in val.split(",") if w.strip()]


def parse_related(val: str) -> List[tuple[str, int]]:
    """Parse verwandte_kategorien, returns list of (path_or_id, weight)."""
    out = []
    for p in val.split(","):
        p = p.strip()
        if ":" in p:
            ref, weight_str = p.rsplit(":", 1)
            try:
                out.append((ref.strip(), int(weight_str.strip())))
            except ValueError:
                continue
    return out


# Timestamp für diese Konvertierung
RUN_TS = datetime.datetime.now(datetime.timezone.utc)
RUN_TS_BYTES = int(RUN_TS.timestamp() * 1000).to_bytes(6, "big")


def make_ulid(text: str) -> str:
    """Deterministische ULID: Timestamp jetzt, Randomness aus SHA1 der ID."""
    digest = hashlib.sha1(text.encode("utf-8")).digest()
    return str(ulid.from_bytes(RUN_TS_BYTES + digest[:10]))


def build_graph(raw_nodes: List[Dict[str, Any]]) -> tuple[List[Dict], List[Dict]]:
    """
    Wandelt raw nodes in normalisierte Nodes + Edges um.
    Returns: (nodes_list, edges_list)
    """
    # Schritt 1: Bereinige Pfade (drop "kategorien" prefix)
    cleaned = []
    for n in raw_nodes:
        path = n["path"]
        if path and path[0] == "kategorien":
            path = path[1:]
        if not path:
            continue
        cleaned.append({
            "path": path,
            "level": n["level"],
            "title": n["title"],
            "fields": n["fields"]
        })
    
    # Schritt 2: Baue Lookup path -> id
    # ID ist +name oder letztes Pfad-Segment
    path_to_id: Dict[str, str] = {}
    for c in cleaned:
        path_key = "/".join(c["path"])
        node_id = c["fields"].get("name") or c["path"][-1]
        path_to_id[path_key] = node_id
    
    # Schritt 3: Baue Reverse-Lookup für related-Auflösung
    # Wir brauchen: "gesundheit/mentale_gesundheit" -> "mentale_gesundheit"
    # Aber auch: "mentale_gesundheit" -> "mentale_gesundheit" (direkte ID)
    def resolve_ref(ref: str) -> Optional[str]:
        """Löst einen Pfad oder eine ID zu einer Node-ID auf."""
        # Ist es ein bekannter Pfad?
        if ref in path_to_id:
            return path_to_id[ref]
        # Ist es eine direkte ID?
        all_ids = set(path_to_id.values())
        if ref in all_ids:
            return ref
        # Ist es das letzte Segment eines Pfads?
        last_seg = ref.split("/")[-1]
        if last_seg in all_ids:
            return last_seg
        # Nicht gefunden
        return None
    
    # Schritt 4: Generiere Nodes und Edges
    nodes_list: List[Dict[str, Any]] = []
    edges_list: List[Dict[str, Any]] = []
    
    for c in cleaned:
        path_key = "/".join(c["path"])
        node_id = path_to_id[path_key]
        fields = c["fields"]
        
        # Node erstellen
        node: Dict[str, Any] = {
            "id": node_id,
            "ulid": make_ulid(node_id),
            "title": c["title"],
        }
        
        # Optionale Felder
        if "beschreibung" in fields:
            node["description"] = fields["beschreibung"]
        if "schlagworte" in fields:
            node["keywords"] = parse_keywords(fields["schlagworte"])
        if "themen_wichtigkeit" in fields:
            try:
                node["importance"] = int(fields["themen_wichtigkeit"])
            except ValueError:
                pass
        if "veraenderungstempo" in fields:
            try:
                node["decay"] = int(fields["veraenderungstempo"])
            except ValueError:
                pass
        if "nutzungsfokus" in fields:
            try:
                node["usage"] = int(fields["nutzungsfokus"])
            except ValueError:
                pass
        
        nodes_list.append(node)
        
        # Parent-Edge (aus Pfad-Hierarchie)
        if len(c["path"]) > 1:
            parent_path = "/".join(c["path"][:-1])
            parent_id = path_to_id.get(parent_path)
            if parent_id:
                edges_list.append({
                    "from": parent_id,
                    "to": node_id,
                    "type": "parent_of",
                    "weight": 10  # Hierarchie ist stark
                })
        
        # Related-Edges
        if "verwandte_kategorien" in fields:
            for ref, weight in parse_related(fields["verwandte_kategorien"]):
                target_id = resolve_ref(ref)
                if target_id:
                    edges_list.append({
                        "from": node_id,
                        "to": target_id,
                        "type": "related",
                        "weight": weight
                    })
                else:
                    print(f"Warning: Unresolved reference '{ref}' in {node_id}")
    
    return nodes_list, edges_list


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default="taxonomy.md")
    ap.add_argument("--output-nodes", default="taxonomy.nodes.json")
    ap.add_argument("--output-edges", default="taxonomy.edges.json")
    args = ap.parse_args()

    text = pathlib.Path(args.input).read_text(encoding="utf-8")
    raw_nodes = parse_file(text)
    nodes, edges = build_graph(raw_nodes)

    # Sortiere für deterministische Ausgabe
    nodes.sort(key=lambda n: n["id"])
    edges.sort(key=lambda e: (e["from"], e["to"], e["type"]))

    pathlib.Path(args.output_nodes).write_text(
        json.dumps(nodes, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    pathlib.Path(args.output_edges).write_text(
        json.dumps(edges, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    
    print(f"Written {args.output_nodes} ({len(nodes)} nodes)")
    print(f"Written {args.output_edges} ({len(edges)} edges)")


if __name__ == "__main__":
    main()