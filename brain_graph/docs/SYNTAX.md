# PKMS - Syntax Spezifikation

Version: 1.0
Datum: 2025-11-22

---

## Übersicht

PKMS verwendet eine spezielle Markdown-Syntax für Tags, Attribute, Marker und Links. Diese Spezifikation definiert alle syntaktischen Elemente und deren Parsing-Regeln.

---

## 1. Tags

### 1.1 Grundsyntax

**Format:** `#tag` oder `#kategorie`

**Beispiele:**

```markdown
... #python #technologie #gesundheit
```

### 1.2 Erlaubte Zeichen

**Regel:** Tags dürfen enthalten:

- Buchstaben: `a-z`, `A-Z`
- Zahlen: `0-9`
- Sonderzeichen: `_`, `-`
- Umlaute: `ä`, `ö`, `ü`, `Ä`, `Ö`, `Ü`, `ß`
- Hierarchie-Trenner: `/`

**Regex-Pattern:**

```regex
#[a-zA-Z0-9_\-äöüÄÖÜß]+(?:/[a-zA-Z0-9_\-äöüÄÖÜß]+)*
```

**Verboten:**

- Leerzeichen (verwende stattdessen `-` oder `_`)
- Satzzeichen (`.`, `,`, `!`, `?`, etc.)
- Klammern (`(`, `)`, `[`, `]`, `{`, `}`)

### 1.3 Hierarchie

Tags dürfen NICHT hierarchisch sein.

### 1.4 Verwendung im Text

**Inline:**

```markdown
Ich habe heute Python gelernt. #python #lernen
```

**Mehrfach-Tags:**

```markdown
... #python #technologie #lernen
```

Tags können überall im Text stehen, auch mehrfach, jedoch immer ohne Leerzeichen und nicht am Zeilenanfang, um Verwechslungen mit Überschriften zu vermeiden.

### 1.5 Tag-Extraktion

**Algorithmus:**

```bash
grep -oRE "#[a-zA-Z0-9_\-äöüÄÖÜß/]+" vault/ | sort -u
```

**Python:**

```python
import re
tags = re.findall(r'#[a-zA-Z0-9_\-äöüÄÖÜß/]+', content)
```

### 1.6 Tags vs. Taxonomie-Kategorien

**Wichtig:** Tags und Kategorien sind NICHT dasselbe!

**Tags (#tag):**

- User-definiert, freestyle
- Für grep-Suche und persönliche Organisation
- Keine Vorgaben, keine Struktur nötig
- Beispiel: `#idee`, `#wichtig`, `#todo`

**Taxonomie-Kategorien:**

- Kommen aus TAXONOMY.md
- Bestimmt durch automatisches Matching durch Taxonomy-Matcher

**Unterschied:**

```markdown
# User schreibt:
Heute habe ich Python gelernt. #python #lernen

# Taxonomy-Matcher setzt (automatisch):
"categories": [
    "betriebssysteme",
    "linux"
]
```

---

## 2. Ortsangaben

### 2.1 Grundsyntax

**Format:** `@ort`

**Beispiele:**

```markdown
@Berlin
@Home
@Office
@München
@Cafe_Central
```

### 2.2 Erlaubte Zeichen

**Regel:** Ortsangaben dürfen enthalten:

- Buchstaben: `a-z`, `A-Z`
- Zahlen: `0-9`
- Sonderzeichen: `_`, `-`
- **Keine Leerzeichen** (verwende `_`)

**Regex-Pattern:**

```regex
@[a-zA-Z0-9_\-]+
```

### 2.3 Verwendung im Text

**Inline:**

```markdown
Meeting mit Max @Office um 14:00.
Urlaub @Mallorca vom 01.12. bis 15.12.
```

**Mehrfach:**

```markdown
Roadtrip @Berlin @Hamburg @München
```

### 2.4 Extraktion

**Bash:**

```bash
grep -oRE "@[a-zA-Z0-9_\-]+" vault/ | sort -u
```

**Python:**

```python
import re
locations = re.findall(r'@[a-zA-Z0-9_\-]+', content)
```

### 2.5 Zweck

- Geografische/physische Orte/Organisationen markieren
- Suche nach allen Notizen zu einem Ort
- Kontext für Tasks/Events

**Beispiel:**

```markdown
> [T] Reifenwechsel Termin ausmachen @Auto_Werkstatt_Meier
```

---

## 3. Personen

### 3.1 Grundsyntax

**Format:** `&person`

**Beispiele:**

```markdown
&Max_Mustermann
&Maria
&Dr_Schmidt
&Team_PKMS
```

### 3.2 Erlaubte Zeichen

**Regel:** Personen-Referenzen dürfen enthalten:

- Buchstaben: `a-z`, `A-Z`
- Zahlen: `0-9`
- Sonderzeichen: `_`, `-`
- **Keine Leerzeichen** (verwende `_`)

**Regex-Pattern:**

```regex
&[a-zA-Z0-9_\-]+
```

### 3.3 Verwendung im Text

**Inline:**

```markdown
Meeting mit &Max_Mustermann und &Maria über Projekt PKMS.
Empfehlung von &Dr_Schmidt: Python-Kurs machen.
```

**Mehrfach:**

```markdown
Team-Meeting mit &Max &Maria &Jonas
```

### 3.4 Extraktion

**Bash:**

```bash
grep -oRE "&[a-zA-Z0-9_\-]+" vault/ | sort -u
```

**Python:**

```python
import re
people = re.findall(r'&[a-zA-Z0-9_\-]+', content)
```

### 3.5 Zweck

- Personen/Kontakte markieren
- Suche nach allen Notizen zu einer Person
- Soziale Verbindungen tracken

**Beispiel:**

```markdown
> [T] &Max anrufen wegen Projekt-Update @Home
```

---

## 4. Attribute

### 4.1 Grundsyntax

**Format:** `+key:value`

**Beispiele:**

```markdown
+datum:20241122
+projekt:pkms_zero
+important:9
+autor:max_mustermann
```

### 4.2 Erlaubte Zeichen

**Key:**

- Buchstaben: `a-z`, `A-Z`
- Zahlen: `0-9`
- Sonderzeichen: `_`, `-`
- **Keine Leerzeichen**

**Value:**

- Alle Zeichen bis zum nächsten Leerzeichen oder Zeilenende
- Bei Leerzeichen im Value: Verwende Unterstriche

**Regex-Pattern:**

```regex
\+([a-zA-Z0-9_\-]+):([^\s]+)
```

### 4.3 Greedy vs. Non-Greedy Parsing

**Greedy (am Zeilenanfang):**

Attribute am Zeilenanfang werden "greedy" geparst - der Value geht bis zum Zeilenende:

```markdown
+datum:2024-11-22
+projekt:PKMS Implementation Phase 1
+autor:Max Mustermann
```

**Regex für Greedy:**

```regex
^\+([a-zA-Z0-9_\-]+):(.+)$
```

**Non-Greedy (im Fließtext):**

Attribute im Fließtext werden "non-greedy" geparst - der Value endet beim ersten Leerzeichen:

```markdown
Das Meeting war am +datum:2024-11-22 und dauerte 2 Stunden.
```

**Regex für Non-Greedy:**

```regex
\+([a-zA-Z0-9_\-]+):([^\s]+)
```

### 4.4 Spezielle Attribute

**Standard-Attribute:**

- `+id:ULID` - Eindeutige Identifikation (siehe 4.6)
- `+prio:1-10` - Wichtigkeit (1=niedrig, 10=hoch)
- `+datum:YYYY-MM-DD` - Datum (ISO 8601 mit Trennzeichen)
- `+projekt:name` - Projekt-Referenz
- `+quelle:url` - URL oder Referenz
- `+status:wert` - Status (z.B. todo, erledigt, archiviert)

**Link-Attribute:**

- `+image:ULID` - Bild-Referenz (siehe `specs/LINK_SYNTAX.md`)
- `+link:ULID` - Notiz-Referenz
- `+link:(Beschreibung)` - LLM-aufgelöste Referenz

### 4.5 Attribute-Extraktion

**Greedy (Zeilenanfang):**

```bash
grep -oRE "^\+[a-zA-Z0-9_\-]+:.+$" vault/
```

**Non-Greedy (Fließtext):**

```bash
grep -oRE "\+[a-zA-Z0-9_\-]+:[^\s]+" vault/
```

**Python:**

```python
import re

# Greedy
greedy_attrs = re.findall(r'^\+([a-zA-Z0-9_\-]+):(.+)$', content, re.MULTILINE)

# Non-Greedy
non_greedy_attrs = re.findall(r'\+([a-zA-Z0-9_\-]+):([^\s]+)', content)
```

### 4.6 Identifikation (ULID)

Jede Notiz **muss** eine eindeutige ID (ULID) besitzen.

**Syntax:**

```markdown
# Titel der Notiz

+id:01HAR6DP2M7G1KQ3Y3VQ8C0Q
```

**Regeln:**

1. Die ID muss als Attribut `+id:ULID` angegeben werden.
2. Sie muss **direkt unter dem H1-Titel** stehen (1 Leerzeile Abstand).
3. Sie ist das **einzige** Metadatum an dieser Stelle (andere Attribute werden in eine separaten *.md.meta.json abgelegt).
4. Die ID darf **nicht** manuell geändert werden.

---

## 5. Marker

### 5.1 Grundsyntax

**Analog (Scan/Handschrift):**

```text
? | Wie funktioniert LSH?
T | Termin für Reifenwechsel ausmachen
I | Neue Idee: Python-basierte PKM
K | Suche nach Python Tutorials
L | Korrigiere Tippfehler in dieser Notiz
```

**Digital (Markdown):**

```markdown
> [?] Wie funktioniert LSH?
> [T] Termin für Reifenwechsel ausmachen
> [D] Neue Idee: Python-basierte PKM
> [B] Suche nach Python Tutorials
> [L] Korrigiere Tippfehler in dieser Notiz
```

### 5.2 Marker-Typen

| Marker | Name | Funktion | Agent |
|--------|------|----------|-------|
| `?` / `[?]` | Assistentin | Beantwortet Fragen inline | Marker-Agent |
| `T` / `[T]` | **T**ask-Managerin | Erstellt Task in `todos/` | Marker-Agent |
| `D` / `[D]` | **D**okumentarin | Erstellt neue Notiz oder Link | Marker-Agent |
| `B` / `[B]` | **B**ibliothekarin | Führt Suche aus | Marker-Agent |
| `L` / `[L]` | **L**ektorin | Korrigiert Text, Tags, Attribute | Marker-Agent |
| `F` / `[F]` | **F**orscherin | Führt Recherchen & Suchen im Web durch | Marker-Agent |
| `K` / `[K]` | **K**alender-Assistentin | Erstellt Kalendereintrag | Marker-Agent |

### 5.3 Analog-Format

**Syntax:** `MARKER | TEXT`

**Regeln:**

- Vertikale Linie `|` trennt Marker von Text
- Leerzeichen um `|` sind optional
- Nur am Zeilenanfang

**Regex:**

```regex
^([?TIKL])\s*\|\s*(.+)$
```

### 5.4 Digital-Format

**Syntax:** `> [MARKER] TEXT`

**Regeln:**

- Blockquote `>` am Anfang
- Marker in eckigen Klammern `[?]`
- Leerzeichen nach `]`

**Regex:**

```regex
^>\s*\[([?TIKL])\]\s*(.+)$
```

### 5.5 Transformation (Analog → Digital)

**Input (analog):**

```text
? | Wie schwer ist ein Elefant?
```

**Output (digital):**

```markdown
> [?] Wie schwer ist ein Elefant?
>
> Ein afrikanischer Elefant wiegt zwischen 4.000-7.000 kg,
> ein asiatischer Elefant zwischen 2.000-5.000 kg.
>
> [Quelle: Wikipedia](https://de.wikipedia.org/wiki/Elefant)
```

**Regel:**

- Analog wird zu Digital konvertiert
- Antwort wird als Blockquote-Fortsetzung hinzugefügt
- Leerzeile zwischen Frage und Antwort

### 5.6 Marker-Status

**Unverarbeitet:**

```markdown
? | Frage hier
```

oder

```markdown
> [?] Frage hier
```

**Verarbeitet:**

```markdown
> [?] Frage hier
>
> Antwort hier
```

**Validierung:** Marker ohne Antwort = unverarbeitet (Validierungs-Agent warnt).

---

## 6. Links

### 6.1 Link-Typen

Vollständige Dokumentation siehe: `specs/LINK_SYNTAX.md`

**Kurz-Übersicht:**

| Syntax | Zweck | Beispiel |
|--------|-------|----------|
| `+image:HAR6DP` | Bild-Referenz (4-stellige Kurz-ID) | `+image:01HAR6DP...` (Skript vervollständigt) |
| `+link:3X1MK2` | Notiz-Referenz (4-stellige Kurz-ID) | `+link:01G3X1MK...` (Skript vervollständigt) |
| `+link:(Beschreibung)` | LLM-aufgelöste Referenz | `+link:01G3X1MK...` (Skript sucht & ersetzt) |
| `+projekt:8C0Q` | Generisches Attribut mit ULID | `+projekt:01HAR6...` (Skript vervollständigt) |

### 6.2 ULID-Format

**Vollständig:** 26 Zeichen (Base32-kodiert)

```
01HAR6DP2M7G1KQ3Y3VQ8C0Q
```

**Kurz-ID:** Letzte 4 Zeichen

```
8C0Q
```

### 6.3 Link-Auflösung

User schreibt Kurz-ID, Skript vervollständigt zu voller ULID.

---

## 7. Dateinamen

### 7.1 Format

**Regel:** `themen-slug--{kurz-id}.md`

**Beispiele:**

```
projekt-pkms-meeting--8C0Q1X.md
python-virtual-environments--3X1MCQ.md
gesundheit-laufen-training--5Y7K8C.md
```

### 7.2 Komponenten

**Slug:**

- Beschreibender Name (lowercase)
- Wörter getrennt durch `-`
- Keine Leerzeichen, keine Sonderzeichen
- Keine Umlaute (verwende ae, oe, ue)

**Kurz-ID:**

- Letzte 6 Zeichen der ULID
- Großbuchstaben + Zahlen (Base32)
- Durch `--` vom Slug getrennt

### 7.3 Slug-Generierung

**Regeln:**

1. Titel → lowercase
2. Leerzeichen → `-`
3. Sonderzeichen entfernen
4. Umlaute ersetzen: ä→ae, ö→oe, ü→ue, ß→ss
5. Mehrfach-`-` reduzieren auf einfach-`-`
6. Max. 50 Zeichen

**Beispiel:**

```
"Python Virtual Environments - Setup Guide"
→ "python-virtual-environments-setup-guide"
```

### 7.4 ULID-Matching

**Validierung:** Kurz-ID im Dateinamen muss mit ULID übereinstimmen.

**Check:**

```python
import re

filename = "projekt-pkms--VQ8C0Q.md"
filename_short_id = re.search(r'--([A-Z0-9]{6})\.md$', filename).group(1)  # "VQ8C0Q"

ulid = "01HAR6DP2M7G1KQ3Y3VQ8C0Q"
short_id = ulid[-6:]  # "VQ8C0Q"

assert short_id == filename_short_id, "Mismatch!"
```

---

## 8. Escape-Regeln

### 8.1 Wörtliches `#`

**Problem:** User möchte `#` schreiben, ohne einen Tag zu erstellen.

**Lösung:** Backslash-Escape

```markdown
Das ist ein \#hashtag, aber kein Tag.
```

**Parsing:** `\#` wird nicht als Tag erkannt.

**Regex:**

```regex
(?<!\\)#[a-zA-Z0-9_\-äöüÄÖÜß/]+
```

### 8.2 Wörtliches `+`

**Problem:** User möchte `+key:value` schreiben, ohne ein Attribut zu erstellen.

**Lösung:** Backslash-Escape

```markdown
Die Formel ist: x = y \+delta
```

**Parsing:** `\+` wird nicht als Attribut erkannt.

**Regex:**

```regex
(?<!\\)\+[a-zA-Z0-9_\-]+:[^\s]+
```

### 8.3 Wörtliches `@`

**Problem:** User möchte `@` schreiben, ohne eine Ortsangabe zu erstellen.

**Lösung:** Backslash-Escape

```markdown
Das kostet 10\@ (at-Symbol), nicht ein Ort.
```

**Parsing:** `\@` wird nicht als Ortsangabe erkannt.

**Regex:**

```regex
(?<!\\)@[a-zA-Z0-9_\-]+
```

### 8.4 Wörtliches `&`

**Problem:** User möchte `&` schreiben, ohne eine Personen-Referenz zu erstellen.

**Lösung:** Backslash-Escape

```markdown
Dies ist ein \&-Zeichen (kaufmännisches Und).
```

**Parsing:** `\&` wird nicht als Personen-Referenz erkannt.

**Regex:**

```regex
(?<!\\)&[a-zA-Z0-9_\-]+
```

### 8.5 Code-Blöcke

**Regel:** Tags/Attribute in Code-Blöcken werden **nicht** geparst.

**Beispiel:**

````markdown
```python
# Dies ist ein Kommentar, kein Tag
x = +5  # Dies ist kein Attribut
```
````

**Parsing:** Ignore alles zwischen ` ```...``` `.

### 8.6 HTML-Kommentare

**Regel:** Tags/Attribute/Ortsangaben/Personen in HTML-Kommentaren werden **nicht** geparst.

**Beispiel:**

```markdown
<!-- #debug +test:123 @Berlin &Max -->
```

**Parsing:** Ignore alles zwischen `<!--...-->`.

---

## 9. Parsing-Algorithmus

### 9.1 Reihenfolge

1. **Extrahiere Code-Blöcke** (zum Ignorieren)
2. **Extrahiere HTML-Kommentare** (zum Ignorieren)
3. **Parse Tags** (`#...`)
4. **Parse Ortsangaben** (`@...`)
5. **Parse Personen** (`&...`)
6. **Parse Attribute** (`+key:value`, greedy/non-greedy)
7. **Parse Marker** (`?|...` oder `> [?]...`)
8. **Parse Links** (`+image:...`, `+link:...`)
9. **Extrahiere Footer** (System-Metadaten)

### 9.2 Beispiel-Code (Python)

```python
import re

def parse_note(content):
    # Remove code blocks
    code_blocks = re.findall(r'```.*?```', content, re.DOTALL)
    for block in code_blocks:
        content = content.replace(block, '')

    # Remove HTML comments
    content = re.sub(r'<!--.*?-->', '', content, flags=re.DOTALL)

    # Extract tags
    tags = re.findall(r'(?<!\\)#[a-zA-Z0-9_\-äöüÄÖÜß/]+', content)

    # Extract locations
    locations = re.findall(r'(?<!\\)@[a-zA-Z0-9_\-]+', content)

    # Extract people
    people = re.findall(r'(?<!\\)&[a-zA-Z0-9_\-]+', content)

    # Extract attributes (greedy)
    greedy_attrs = re.findall(r'^\+([a-zA-Z0-9_\-]+):(.+)$', content, re.MULTILINE)

    # Extract attributes (non-greedy)
    non_greedy_attrs = re.findall(r'(?<!\\)\+([a-zA-Z0-9_\-]+):([^\s]+)', content)

    # Extract markers
    analog_markers = re.findall(r'^([?TIKL])\s*\|\s*(.+)$', content, re.MULTILINE)
    digital_markers = re.findall(r'^>\s*\[([?TIKL])\]\s*(.+)$', content, re.MULTILINE)

    return {
        'tags': tags,
        'locations': locations,
        'people': people,
        'greedy_attrs': greedy_attrs,
        'non_greedy_attrs': non_greedy_attrs,
        'analog_markers': analog_markers,
        'digital_markers': digital_markers
    }
```

### 9.3 Performance

**Optimierungen:**

- Verwende `grep -F` für exakte Matches (schneller als Regex)
- Cache Footer-Extraktion (primary-cat, hash)
- Lazy Parsing: Nur parse, was nötig ist

---

## 10. Validierung

### 10.1 Tag-Validierung

**Check:** Alle Tags müssen Pattern entsprechen.

```python
invalid_tags = [t for t in tags if not re.match(r'^#[a-zA-Z0-9_\-äöüÄÖÜß/]+$', t)]
```

**Fehler:**

- `#tag with spaces` → Ungültig
- `#tag!` → Ungültig (Satzzeichen)

### 10.2 Attribut-Validierung

**Check:** Key muss alphanumerisch sein, Value darf nicht leer sein.

```python
for key, value in attrs:
    assert re.match(r'^[a-zA-Z0-9_\-]+$', key), f"Invalid key: {key}"
    assert value.strip(), f"Empty value for key: {key}"
```

### 10.3 Marker-Validierung

**Check:** Alle Marker müssen verarbeitet sein (= Antwort vorhanden).

**Unverarbeitet:**

```markdown
> [?] Frage ohne Antwort
```

**Fehler:** Validierungs-Agent warnt.

### 10.4 ULID-Validierung

**Check:** Dateiname-ULID muss mit ULID übereinstimmen.

```python
filename_short = extract_short_id_from_filename(filename)
ulid = extract_ulid(content)
assert ulid.endswith(filename_short), "ULID mismatch!"
```

---

## 11. Zusammenfassung

| Element | Syntax | Regex | Beispiel |
|---------|--------|-------|----------|
| **Tag** | `#tag` | `#[a-zA-Z0-9_\-äöüÄÖÜß/]+` | `#python` |
| **Ortsangabe** | `@ort` | `@[a-zA-Z0-9_\-]+` | `@Berlin` |
| **Person** | `&person` | `&[a-zA-Z0-9_\-]+` | `&Max_Mustermann` |
| **Attribut (Greedy)** | `+key:value` | `^\+([a-zA-Z0-9_\-]+):(.+)$` | `+datum:2024-11-22` |
| **Attribut (Non-Greedy)** | `+key:value` | `\+([a-zA-Z0-9_\-]+):([^\s]+)` | `+datum:20241122` |
| **Marker (Analog)** | `? \| text` | `^([?TIKL])\s*\|\s*(.+)$` | `? \| Frage` |
| **Marker (Digital)** | `> [?] text` | `^>\s*\[([?TIKL])\]\s*(.+)$` | `> [?] Frage` |
| **Link** | `+image:ULID` | `\+image:([A-Z0-9]{4,26})` | `+image:HAR6` |
| **Footer** | `<!-- key: value -->` | `<!-- ([a-z\-]+): (.+?) -->` | `<!-- hash: abc123 -->` |
| **Dateiname** | `slug--ID.md` | `^[a-z0-9\-]+--[A-Z0-9]{4}\.md$` | `python-guide--8C0Q.md` |

---

## 12. Best Practices

### 12.1 Tag-Konventionen

- **Konsistente Schreibweise:** Immer lowercase, außer Namen/Akronyme
- **Nicht zu spezifisch:** `#python` statt `#python_3_11_tutorial_video`

### 12.2 Ortsangaben-Konventionen

- **Konsistente Namen:** `@Home` statt mal `@home`, mal `@Home`
- **Spezifisch genug:** `@Office_Berlin` statt nur `@Office` (wenn mehrere Büros)

### 12.3 Personen-Konventionen

- **Vollständige Namen:** `&Max_Mustermann` statt `&Max`
- **Konsistente Schreibweise:** Immer gleiche Schreibweise pro Person
- **Gruppen markieren:** `&Team_PKMS` für Teams/Gruppen

### 12.4 Attribut-Konventionen

- **Standardisierte Keys:** `+datum`, `+projekt`, `+important`
- **ISO-Datumsformat:** `+datum:2024-11-22` (YYYY-MM-DD)
- **Keine Redundanz:** Nicht `+datum:2024-11-22 +year:2024`

### 12.5 Marker-Konventionen

- **Nur eine Frage pro Marker:** Nicht "? | Frage 1? Frage 2?"
- **Präzise Formulierung:** "? | Wie funktioniert X?" statt "? | X?"
- **Tasks mit Context:** "T | Meeting mit @Max &Maria #projekt_pkms"

### 12.6 Link-Konventionen

- **Verwende Kurz-IDs:** `+link:3X1MB1` statt volle ULID (Script vervollständigt)
- **Beschreibende Links bei Unsicherheit:** `+link:(Python venv guide)`
- **Context bei Bildern:** Text vor `+image:HAR6XC` erklärt das Bild

---

**Ende der Syntax-Spezifikation**
