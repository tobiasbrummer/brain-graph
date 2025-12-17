# Organisches PKMS: Architektur & Dynamik

+status:draft
+version:2.0
+date:2025-12-17
+author:&User
+context:System-Definition

## 1. Philosophie: Das kognitive Exoskelett

Dieses PKMS ist kein statisches Archiv, sondern ein **lebendes System**, das biologische Prinzipien des menschlichen Gehirns nachahmt. Es unterscheidet zwischen flüchtigem Arbeitsgedächtnis (Chats) und konsolidiertem Langzeitwissen (Notizen). Die Struktur ist nicht starr, sondern **neuroplastisch**: Verbindungen, die genutzt werden, verstärken sich; ungenutzte Pfade verblassen, aber wichtige Erinnerungen werden aktiv wachgehalten.

## 2. Akteure: Agents als Kollegen (`&Agent`)

KI-Agenten sind keine unsichtbaren Backend-Skripte, sondern sichtbare **Entities** im Wissensgraphen. Sie werden syntaktisch wie menschliche Mitarbeiter behandelt.

### 2.1 Syntax & Identität

* **Symbol:** `&` (Ampersand) für alle Akteure (Menschen & Maschinen).
* **Beispiele:** `&Max_Mustermann` (Mensch), `&Gardener` (KI), `&Research_Bot` (KI).
* **Schema:** `entity.schema.json` mit `entity_type: "AGENT"`.

### 2.2 Agent-Definition (Konfiguration via Markdown)

Ein Agent existiert erst, wenn er durch eine Profil-Notiz definiert wurde. Diese Notiz dient als Konfiguration und System-Prompt.

**Beispiel `system/agents/gardener.md`:**

```markdown
# &Gardener

+type:agent_profile
+model:gpt-4o
+status:active
+capabilities:read_graph, write_tags, merge_nodes

Der &Gardener ist zuständig für die Pflege der Taxonomie. Er identifiziert Cluster in Tags und schlägt neue Kategorien vor.

## System Prompt
Du bist ein erfahrener Wissensmanager. Deine Aufgabe ist es...

```

### 2.3 Provenance (Herkunftsnachweis)

Jedes Dokument zeigt transparent, wer es erstellt oder bearbeitet hat.

* `+author:&Research_Bot` -> Erzeugt Edge `authored_by`
* `+reviewed_by:&User` -> Erzeugt Edge `reviewed_by`

---

## 3. Gedächtnis-Modell: Chats & Konsolidierung

Das System unterscheidet strikt zwischen **Input-Strom** (Working Memory) und **Wissens-Basis** (Long-term Memory).

### 3.1 Chats (Working Memory)

* **Natur:** Flüchtig, unstrukturiert, zeitbasiert.
* **Behandlung:** Hohe *Decay-Rate* (Vergessen).
* **Ziel:** Dienen nur als Rohmaterial. Wenn sie nicht verarbeitet werden, sinken sie im Ranking ins Bodenlose (Archiv).

### 3.2 Der Destillations-Prozess (Träumen)

Ein Agent (z. B. `&Archivist`) analysiert nachts neue Chats (Status: `active`) und extrahiert Fakten.

1. **Input:** `chat_session_123.json`
2. **Extraktion:** Agent erstellt saubere Notizen/Chunks.
3. **Verknüpfung:** Die neuen Notizen erhalten `+derived_from:chat_session_123`.
4. **Abschluss:** Chat erhält Status `processed` und wird archiviert.

---

## 4. Evolution: Von Tags zu Kategorien

Die Struktur wächst "Bottom-Up". Es gibt keine erzwungene Taxonomie, sondern eine organische Entwicklung von einer Folksonomie (Tags) hin zur Taxonomie (Kategorien).

### 4.1 Der Lebenszyklus eines Themas

1. **Phase 1: Tagging (Folksonomie)**

* Nutzer schreibt: `Das ist wichtig für #projekt_x`.
* System: Speichert String `"projekt_x"` im `tags`-Array des Chunks. Keine Graph-Node.

2. **Phase 2: Wachstum**

* Der Tag `#projekt_x` taucht in 10 verschiedenen Dokumenten auf.
* Der `&Gardener` erkennt das Cluster.

3. **Phase 3: Promotion (Kristallisation)**

* `&Gardener` fragt: "Soll `#projekt_x` eine Kategorie werden?"
* Bei Bestätigung:
* Erstellung einer Node in `taxonomy.schema.json`.
* Konvertierung aller Strings `#projekt_x` zu echten Edges (`categorized_as`).
* Der Tag ist nun ein festes Konzept im "Gehirn" des Systems.

---

## 5. Neuroplastizität: Dynamische Gewichtung

Wissen verfällt nicht linear. Es folgt dem Prinzip "Use it or lose it", ergänzt durch "Spaced Repetition".

### 5.1 Der "Synaptic Weight" Score

Jeder Node hat ein dynamisches Gewicht (W), das die Sichtbarkeit in der Suche und für Agents bestimmt.

* **Aufwertung (Interaction/Activation):**
* Jeder Klick, jede Bearbeitung und jede Nutzung im Kontext eines Chats erhöht das Gewicht.
* Edges, die oft traversiert werden ("Trampelpfade"), werden stärker.

* **Abwertung (Decay):**
* Ohne Interaktion sinkt das Gewicht über Zeit. Unwichtiges "Rauschen" verschwindet aus dem Suchindex.

### 5.2 Resurfacing (Wiedererinnerung)

Das System verhindert "Daten-Demenz" für wichtige Themen.

* **Regel:** Wenn `Importance = High` ABER `Weight < Threshold` (lange nicht gesehen):
* **Aktion:** Der `&Gardener` spült das Dokument aktiv hoch ("Flashback").
* *"Du hast diese wichtige Notiz seit 2 Jahren nicht angesehen. Ist sie noch aktuell?"*

* **Effekt:** Interaktion setzt den Timer zurück -> Node wird wieder "heiß".

---

## 6. Zusammenfassung der Schemas

### `entity.schema.json`

Erweitert um `entity_type: AGENT` und `agent_profile` (Model, Permissions).

### `edge.schema.json`

Enthält organische Beziehungen:

* `mentions` (Text erwähnt Entity)
* `authored_by` (Entity hat Node erstellt)
* `derived_from` (Notiz stammt aus Chat)
* `categorized_as` (Chunk gehört zu Taxonomie-Node)

### `document.schema.json`

Enthält Lifecycle-Metadaten:

* `lifecycle_stage`: `volatile` (Chat) vs. `crystallized` (Notiz).
* `decay_factor`: Individuelle Vergessenskurve.
