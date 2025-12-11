# PKMS – Automatisierte Aktualisierung, Relevanz-Management und Informations-Synthese  

Stand: 2025-12-08 (aktualisiert)

## Übersicht / Ziele

Dieses Konzept stellt sicher, dass ein reines Markdown-basiertes PKMS langfristig such- und nutzbar bleibt.  
Versionierung erfolgt über Git, automatische Verarbeitung über Git-Hooks.  
Redundanz wird reduziert, Relevanz gewichtet und Wissen über Zeit verdichtet.

## Kernideen

- **Git-Hooks** als zentraler Trigger für alle Datenprozesse  
- **Keine permanente Überwachung** von Dateien (kein iNotify-Chaos)
- **Async Job Queue** für post-commit Verarbeitung (JSON-basiert)
- **Pro-File Parquet-Storage** für Chunks und Embeddings
- **Langfristige Suchqualität** durch dynamisches Ranking & Zusammenfassungen
- **Balance aus Automatisierung und manuellem Review**

---

## Relevanzmodell (Ranking-Faktoren)

| Faktor | Bedeutung | Aktualisierung |
|--------|-----------|----------------|
| Uses | Wie oft wird die Notiz genutzt/verändert | per Git-Hook inkrementieren |
| Importance | Persönliche Wichtigkeit eines Themas | von Taxonomie geerbt oder manuell überschrieben |
| Information Decay | Wie schnell verliert der Inhalt an Relevanz | von Taxonomie geerbt oder manuell gesetzt |
| Recency | Aktualität | dynamisch durch Datumsvergleich |

**Berechnung:**  
Keine Speicherung der abgeleiteten Werte; sie werden zur DB-Init-Zeit berechnet und in temporärer Tabelle materialisiert.

**Formel-Beispiel:**

```
relevance_score = (
    importance * 0.4 + 
    uses * 0.2 + 
    (1.0 / (1.0 + decay * days_since_modified / 365.0)) * 0.4
)
```

---

## Taxonomie-basierte Metadaten-Vererbung

### Struktur

- Kategorien haben optionale Metadaten: `importance`, `decay`, `usage`
- Notizen referenzieren Kategorien via `categories: [cat1, cat2, ...]`
- Vererbung erfolgt automatisch beim Processing

### Vererbungsregel

**Bei mehreren Kategorien**: Die Kategorie mit der **höchsten importance** bestimmt die geerbten Werte.

### Frontmatter-Schema

```yaml
---
created: 2025-12-08T10:30:00Z
modified: 2025-12-08T14:20:00Z
uses: 3
categories: [technologie_und_programmierung, wissensverwaltung]

# Optional: Manuelle Überschreibung
importance: 9  # überschreibt inherited value
decay: 6       # überschreibt inherited value
---
```

**Logik**:

1. Wenn `importance`/`decay` im Frontmatter → nutze das
2. Sonst → inherit von Kategorie mit höchster `importance`
3. Wenn keine Kategorie Metadaten hat → default (importance=5, decay=5)

### Beispiel

```yaml
categories: [technologie_und_programmierung, wissensverwaltung]

# Taxonomie:
# - technologie_und_programmierung: importance=9, decay=8
# - wissensverwaltung: importance=7, decay=5

# → Ergebnis: importance=9, decay=8 (von Tech-Kategorie)
```

---

## Automatische Relevanzanpassung

- Importance sinkt **nicht automatisch**, sondern wird über Decay-Faktor in Relevanz-Score eingerechnet
- Änderungen in Frontmatter werden **geloggt** (via Git)
- **Review-Benachrichtigungen** für potenziell gealterte, aber ehemals wichtige Inhalte
- Manuelle Korrektur jederzeit möglich durch Frontmatter-Edit

---

## Informations-Synthese & Redundanzreduktion

Ziel: Zusammengehörige Inhalte früh erkennen und verdichten.

### Dreistufiger Prozess

1. **Clustering / Kategorisierung**
   - Taxonomie + Embeddings
   - Erkennen von Nähe über Similarity-Threshold
2. **Graph-Edges erzeugen**
   - Automatisch per Skript
   - Leichte neuronale Modelle statt LLM
3. **Synthese**
   - Agent generiert Zusammenfassungs-Draft
   - **Manuelles Review erforderlich** vor Commit
   - Ursprungsnotizen behalten Referenz-Edges
   - Importance sinkt bei Einzelnotizen (oder manuell angepasst)
   - Zusammenfassung wird Such-Primärziel

### Ergebnis

- Zentrales Wissensdokument ersetzt verstreutes Fragmentwissen
- Historie bleibt vollständig erhalten (Git + referenzierte Edges)

---

## Automations-Fluss

```
Git Commit
  ↓
Post-Commit Hook erkennt geänderte .md Files
  ↓
Fügt Jobs zu embedding_queue.json hinzu
  ↓
Startet process_queue.py (falls nicht laufend)
  ↓
Worker-Loop:
  ├─ Nimmt Job aus Queue
  ├─ Update Frontmatter (uses++, modified, inherit metadata)
  ├─ Re-Chunk Markdown
  ├─ Generate Embeddings (llama.cpp + jina-embeddings-v2-base-de)
  ├─ Write zu file-spezifischer .parquet
  ├─ Bei Erfolg: Job entfernen
  └─ Bei Fehler: Retry (max 3x) oder Failed-Queue
  ↓
Optional (wöchentlich):
  ├─ Recompute Clusters
  ├─ Identify Synthesis Candidates
  └─ Generate Review Report
```

---

## Storage-Architektur

### File-Based Storage

- **Pro Markdown-File eine Parquet-Datei** (z.B. `note.md` → `note.parquet`)
- Parquet enthält: `chunk_id`, `chunk_text`, `embedding`, `metadata`
- Vorteil: Nur betroffene Files müssen neu geschrieben werden

### DuckDB InMemory Index

- Bei DB-Start: Alle `.parquet` Files laden
- Relevanz-Scores einmalig berechnen und in temporärer Tabelle materialisieren
- Suche nutzt materialisierte Scores (kein Live-Berechnung)

### Queue Management

- `embedding_queue.json` mit drei Listen: `pending`, `processing`, `failed`
- Atomic Updates via Python `json` oder `jq`
- Retry-Logik mit Counter
- Fehler-Logging mit Context

**Queue-Struktur:**

```json
{
  "pending": [
    {
      "file": "notes/pkms-architecture.md",
      "added_at": "2025-12-08T14:30:00Z",
      "commit_hash": "abc123",
      "retry_count": 0
    }
  ],
  "processing": [],
  "failed": [
    {
      "file": "notes/broken.md",
      "error": "Invalid UTF-8",
      "failed_at": "2025-12-08T14:25:00Z",
      "retry_count": 3
    }
  ]
}
```

---

## Implementierungs-Komponenten

### 1. Git Post-Commit Hook

```bash
#!/bin/bash
# .git/hooks/post-commit

QUEUE_FILE=".pkms/embedding_queue.json"

# Initialize queue if not exists
if [ ! -f "$QUEUE_FILE" ]; then
    echo '{"pending":[],"processing":[],"failed":[]}' > "$QUEUE_FILE"
fi

# Get changed markdown files
CHANGED_FILES=$(git diff-tree --no-commit-id --name-only -r HEAD | grep '\.md$')

if [ -z "$CHANGED_FILES" ]; then
    exit 0
fi

# Add to queue
COMMIT_HASH=$(git rev-parse HEAD)
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

for file in $CHANGED_FILES; do
    jq --arg file "$file" \
       --arg commit "$COMMIT_HASH" \
       --arg time "$TIMESTAMP" \
       '.pending += [{"file": $file, "added_at": $time, "commit_hash": $commit, "retry_count": 0}]' \
       "$QUEUE_FILE" > "$QUEUE_FILE.tmp" && mv "$QUEUE_FILE.tmp" "$QUEUE_FILE"
done

# Start processor if not running
if ! pgrep -f "process_queue.py" > /dev/null; then
    nohup python3 process_queue.py >> .pkms/logs/processor.log 2>&1 &
fi
```

### 2. Queue Processor

- Python Script mit Worker-Loop
- Lädt Taxonomie beim Start
- Verarbeitet Jobs sequenziell
- Retry-Logik für Failed Jobs
- Logging aller Operationen

### 3. Chunker & Embedder

- Bestehende Tools aus deinem PKMS-Stack
- Chunker: Markdown-aware Segmentierung
- Embedder: llama.cpp mit jina-embeddings-v2-base-de (lokal)

### 4. DB Init & Search

```python
def init_db():
    conn = duckdb.connect(':memory:')
    
    # Load all parquets
    for parquet_file in Path('.').rglob('*.parquet'):
        conn.execute(f"CREATE TEMP TABLE IF NOT EXISTS chunks AS SELECT * FROM parquet_scan('{parquet_file}')")
    
    # Compute relevance scores
    conn.execute("""
        CREATE TEMP TABLE relevance_scores AS
        SELECT 
            chunk_id,
            importance,
            uses,
            decay,
            modified,
            julianday('now') - julianday(modified) as days_since_modified,
            (importance * 0.4 + uses * 0.2 + 
             (1.0 / (1.0 + decay * (julianday('now') - julianday(modified)) / 365.0)) * 0.4
            ) as relevance_score
        FROM chunks
    """)
    
    return conn

def search(query: str, top_k: int = 10):
    conn = init_db()
    query_embedding = embed_query(query)
    
    results = conn.execute("""
        SELECT 
            chunk_text,
            array_cosine_similarity(embedding, ?::FLOAT[768]) as similarity,
            relevance_score,
            (similarity * 0.6 + (relevance_score / 10.0) * 0.4) as final_score
        FROM chunks
        JOIN relevance_scores USING (chunk_id)
        ORDER BY final_score DESC
        LIMIT ?
    """, [query_embedding, top_k]).fetchall()
    
    return results
```

---

## Vorteile des Ansatzes

- Skalierbare Suche auch bei stark wachsendem Datenbestand
- Historische Informationen bleiben verfügbar, aber nicht störend
- Redundanz nimmt ab, Klarheit nimmt zu
- Relevanz passt sich dem Leben und Nutzungsmustern an
- Automatisierbar ohne schwergewichtige LLM-Inferenz
- Pro-File Parquet: Nur betroffene Files werden neu geschrieben
- JSON Queue: Einfach, debuggbar, kein zusätzliches DB-System
- Taxonomie-Vererbung: Weniger manuelle Metadaten-Pflege

---

## Offene Erweiterungen (mögliche nächste Schritte)

- Feedback-Loop aus Suchinteraktionen (Ranking-Feinjustierung)
- UI-gestützte Importance-Review-Workflows
- Automatische „Snooze vs. Archive"-Heuristiken für alte Inhalte
- Graph-Visualisierung der Clusterbildung über Zeit
- Cross-Linking Intelligence: Automatisches Vorschlagen interner Links
- Multi-Modal: Bilder/PDFs mit angepasstem Relevanzmodell

---

## Tuning-Parameter (iterativ anpassen)

- **Similarity-Threshold** für Clustering (Start: 0.85)
- **Decay-Faktoren** pro Kategorie (siehe Taxonomie)
- **Relevanz-Formel** Gewichtung (aktuell: 0.4 / 0.2 / 0.4)
- **Combined Search Score** (aktuell: similarity 0.6 + relevance 0.4)
- **Review-Intervall** für Synthese-Kandidaten (Start: wöchentlich)

---

## Kurzfazit

Die Architektur ermöglicht ein **lebendiges**, **selbstheilendes** Markdown-PKMS, das sich an persönliche Prioritäten anpasst, Wissenswachstum unterstützt und langfristig eine hohe Suchqualität sicherstellt. Durch file-basiertes Storage, Git-Integration und taxonomie-gesteuerte Metadaten bleibt das System wartbar, transparent und vollständig unter deiner Kontrolle.
