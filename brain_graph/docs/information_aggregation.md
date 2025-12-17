n# PKMS Phase 3: Kognitive Evolution & Handlungsfähigkeit

+status:draft
+version:3.0
+date:2025-12-17
+author:&User
+context:System-Architecture
+depends_on:[[ORGANIC_DESIGN.md]]

## 1. Vision: Vom Speicher zum Partner

In Phase 3 erhält das organische PKMS drei neue Fähigkeiten, die biologischen Systemen nachempfunden sind:

1. **Träumen (Serendipity):** Aktives Finden von Verbindungen im Schlaf (unüberwachtes Lernen).
2. **Forschung (Validierung):** Überprüfung von "Träumen" durch externe Quellen (Web-Suche).
3. **Reflexe (Handlung):** Fähigkeit, nicht nur Text zu speichern, sondern Aktionen auszuführen (Tools).

Ziel ist ein System, das **Wissen generiert**, statt es nur zu verwalten, und **negatives Wissen** (Fehlschläge) speichert, um Lernen zu ermöglichen.

---

## 2. Der "Traum-Modus" (Active Serendipity)

Wenn die Systemlast niedrig ist (z. B. nachts), analysiert das System die Topologie des Wissensgraphen und die Vektor-Embeddings, um "Latent Bridges" zu finden.

### 2.1 Der Mechanismus

* **Vektor-Anomalien:** Der `&Dreamer` Agent sucht nach Clustern, die mathematisch ähnlich sind (hoher Cosine-Similarity Score), aber im Graphen keine direkte Verbindung (Edge) haben.
* **Hypothesen-Bildung:** Das System formuliert eine Frage: *"Warum sind Cluster A (Biologie) und Cluster B (Netzwerktechnik) ähnlich?"*

### 2.2 Die Akteure

* `&Dreamer`: Ein ML-Skript/Agent, das rein auf Vektor-Ebene arbeitet.
* `&Researcher`: Ein LLM-Agent mit Web-Zugriff, der die Hypothesen des Träumers prüft.

---

## 3. Die wissenschaftliche Methode (Hypothesen-Management)

Das System muss wissen, was *wahr* ist, was *falsch* ist und was noch *ungeprüft* ist. Dazu wird ein neuer Dokumententyp eingeführt.

### 3.1 Dokument-Typ: `hypothesis`

Hypothesen sind persistente Dateien. Auch wenn eine Hypothese widerlegt wird ("rejected"), **bleibt sie gespeichert**. Dies verhindert, dass das System jede Nacht dieselbe falsche Verbindung neu prüft ("Sisyphus-Loop").

**Markdown-Template (`system/hypotheses/hyp--id.md`):**

```markdown
# Hypothese: Zusammenhang Myzel & TCP/IP

+type:hypothesis
+status:rejected
+date:2025-12-17
+checked_by:&Researcher
+valid_until:2026-06-01

## Vermutung
Vektor-Nähe (0.82) zwischen "Pilz-Netzwerke" und "Routing-Protokolle".

## Ergebnis
Recherche ergab keine kausalen Zusammenhänge oder Papers. Ähnlichkeit basiert auf polysemer Nutzung des Wortes "Knoten".

## Entscheidung
Keine Verbindung erstellen. Re-Evaluation frühestens in 6 Monaten.

```

### 3.2 Status-Workflow

1. **Pending:** `&Dreamer` erstellt Datei.
2. **Investigating:** `&Researcher` sucht im Web/arXiv.
3. **Result:**

* **Validated:** Hypothese wird zu `insight` oder `note`. Edge `validated_connection` wird erstellt.
* **Rejected:** Datei bleibt als "Negatives Wissen" erhalten. Edge `investigates` bleibt, aber traversiert nicht.

---

## 4. Reflexe & Sinne (Multimodalität & Tools)

Das System bricht aus der reinen Text-Ebene aus.

### 4.1 Reflexe (Tools)

Agents erhalten in ihrer Definition (`agent_profile`) Zugriff auf APIs.

* **Syntax:** `+tools:calendar_api, mail_api`
* **Trigger:** Ein Dokument-Status wie `+status:schedule_meeting` löst den Reflex aus.
* **Feedback:** Der Agent schreibt das Ergebnis (`> Invite sent.`) zurück in die Notiz.

### 4.2 Sinne (Transducer)

Eingabe-Hürden werden eliminiert, indem Audio und Bild automatisch in "Working Memory" (Text) gewandelt werden.

* **Ohr (`&Transcriber`):** `audio.mp3` -> `transcript.md` -> `summary.md`.
* **Auge (`&Vision_Bot`):** Whiteboard-Foto -> OCR & Mermaid-Diagramm -> `chunk`.

---

## 5. Technische Implementierung (Schema-Updates)

### 5.1 `document.schema.json`

Erweiterung um wissenschaftliche Status-Felder.

```json
{
  "properties": {
    "doc_type": {
      "enum": ["note", "conversation", "insight", "hypothesis"] 
    },
    "research_status": {
      "type": "string",
      "enum": ["pending", "validated", "rejected", "inconclusive"]
    },
    "rejection_reason": { "type": "string" },
    "valid_until": { "type": "string", "format": "date" }
  }
}

```

### 5.2 `edge.schema.json`

Erweiterung um spekulative und validierte Verbindungen.

```json
{
  "type": {
    "enum": [
      "mentions", 
      "related", 
      "investigates",          // Verbindet Hypothese mit Themen
      "predicted_connection",  // Reine ML-Vermutung (schwach)
      "validated_connection"   // Durch &Researcher bestätigt (stark)
    ]
  }
}

```

---

## 6. Beispiel-Workflow: Eine Nacht im PKMS

1. **03:00 Uhr:** Cronjob startet `&Dreamer`.
2. **Scan:** Findet Vektor-Match zwischen `note--urban_planning` und `note--software_circuit_breaker`.
3. **Check:** Prüft Datenbank auf existierende Hypothesen (`type:hypothesis` + `rejected`). Keine gefunden.
4. **Create:** Erstellt `hyp--urban_software.md` (Status: `pending`).
5. **Wake Up:** Weckt `&Researcher`.
6. **Search:** Agent sucht nach "Urban planning flow control vs software engineering patterns".
7. **Find:** Findet Paper über "Traffic Throttling Algorithms".
8. **Update:**

* Setzt `hyp--urban_software.md` auf `status:validated`.
* Erstellt neue Notiz `insight--traffic_throttling_patterns.md`.
* Zieht Edge `validated_connection` zwischen den ursprünglichen Notizen.

9. **User Wake Up:** Der Nutzer findet morgens im "Inbox"-Feed eine neue, fertige Insight-Notiz.

---

## 7. Fazit

Mit Phase 3 wird das PKMS **antifragil**. Es profitiert von Chaos (zufällige Vektor-Nähe), lernt aus Fehlern (Rejected Hypotheses) und nimmt dem Nutzer die mühsamste Arbeit ab: Die Synthese von neuem Wissen aus bestehenden Informationen.
