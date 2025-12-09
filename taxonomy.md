# PKMS Taxonomie

+version:1.0

Diese Datei definiert eine hierarchische Taxonomie für Notizen, um eine automatische Kategorisierung auf Basis der Embeddings zu ermöglichen.

Jede Kategorie hat:

- eine technische Kennung: `+name:`
  - klein, ohne Leerzeichen/Umlaute, statt Leerzeichen Unterstrich `_`
  - dient als **ID** und wird in Referenzen verwendet (keine Pfad-Präfixe)
- optionale Synonyme / Trigger-Wörter: `+schlagworte:`
- optionale Meta-Werte (v. a. bei Oberkategorien):
  - `+themen_wichtigkeit` (1–10)  
  - `+veraenderungstempo` (1–10)  
  - `+nutzungsfokus` (1–10)
- optionale Referenzen auf andere Kategorien: `+verwandte_kategorien:`
- automatisch erzeugte ULID: Zeitanteil = Zeitpunkt der Konvertierung, Randomness = deterministisch aus dem SHA1 der `id`; so lässt sich eine ULID gegen die erwartete `id` verifizieren und für Embeddings als stabiler Key nutzen.
- Ausgabe des Converters: flaches JSON ohne `taxonomy`-Root; Keys sind die Slugs aus `+name`, Kinder stehen als verschachtelte Objekte unter ihrem Parent, Beziehungen enthalten jeweils `id` und `ulid`.

Wenn ein Meta-Wert fehlt, gilt der Default **5** (= neutral).

---

## Bedeutung der Meta-Felder (für Menschen & Agents)

- `+name`  
  Eindeutiger, stabiler **Slug** der Kategorie. Wird in Pfaden und Referenzen verwendet, z. B.  
  `technologie_und_programmierung/programmiersprachen`.

- `+schlagworte`  
  Kommagetrennte Liste von Begriffen (Deutsch/Englisch/Synonyme), die auf diese Kategorie hinweisen.  
  Agents können diese Liste für Klassifikation, Heuristiken und Query-Expansion nutzen.

- `+themen_wichtigkeit` (1–10)  
  „Wie wichtig ist dieses Thema insgesamt?“  
  - 1–3: Randthema, kann im Zweifel niedriger gerankt werden  
  - 4–7: normal wichtig  
  - 8–10: sehr wichtig, soll tendenziell weiter oben erscheinen

- `+veraenderungstempo` (1–10)  
  „Wie schnell ändern sich Inhalte zu diesem Thema?“  
  - 1–3: sehr stabil (Grundlagen, zeitlose Themen)  
  - 4–7: mittel (ändern sich gelegentlich)  
  - 8–10: schnell (Trends, volatile Regelungen, Technik, News)  

  Agents können diesen Wert nutzen, um eine **Freshness / Verfallsrate** im Ranking zu steuern (z. B. schnellere Abwertung alter Notizen bei hohem `veraenderungstempo`).

- `+nutzungsfokus` (1–10)  
  „Wie stark soll tatsächliche Nutzung (z. B. Zugriffshäufigkeit) das Ranking in diesem Thema beeinflussen?“  
  - 1–3: Nutzung ist weniger wichtig (z. B. reine Referenzthemen)  
  - 4–7: Nutzung ist ein Faktor unter mehreren  
  - 8–10: häufig genutzte Notizen sollen deutlich bevorzugt werden

- `+verwandte_kategorien`  
  Liste verwandter Kategorien mit Gewichtung im Bereich 1–10.  
  Syntax (einzeilig, `,` als Trenner):

  ```text
  +verwandte_kategorien: hauptkategorie/unterkategorie:gewicht, andere_kategorie:gewicht
  ```

Bedeutung des Gewichts:

- 1–3: entfernt verwandt
- 4–7: klar verwandt
- 8–10: sehr eng verwandt, fast immer gemeinsam relevant

Agents können diese Gewichte nutzen, um:

- Dokumente in angrenzende Kategorien „mitzuziehen“ (Feature-Propagation)
- bei Suchanfragen benachbarte Themen leicht mitzuboosten
- Kategorie-Ähnlichkeit zwischen Query und Dokument zu berechnen

---

## Hinweise für Agents

- Verwende `+name` als **primäre ID** jeder Kategorie (nicht die Überschrift).
- Nutze `+schlagworte` und die Überschrift, um Notizen Kategorien zuzuordnen.
- Wenn mehrere Kategorien passen, definiere die Zugehörigkeit der Notiz durch eine Bewertung von 1-10. Dabei bevorzuge die mit:
  - höherer `+themen_wichtigkeit`
  - passenderem Kontext (hierarchische Nähe, `+verwandte_kategorien`)
- Beim Ranking kannst du neben dem Text-Score zusätzlich berücksichtigen:
  - `+themen_wichtigkeit` als Boost-Faktor
  - `+veraenderungstempo` zur Berechnung eines Freshness-Faktors
  - `+nutzungsfokus` als Verstärker für Nutzungsdaten (z. B. „uses")
  - `+verwandte_kategorien` zur Berechnung einer Kategorie-Ähnlichkeit

### Automatisch abgeleitete Felder

- **`priority`** wird automatisch aus der Header-Ebene abgeleitet:
  - `##` (Level 2) = priority 2 (höchste Wichtigkeit/Allgemeinheit)
  - `###` (Level 3) = priority 3
  - `####` (Level 4) = priority 4
  - `#####` (Level 5) = priority 5 (spezifischste Ebene)
  - **Regel:** Niedrigere Zahl = höhere Wichtigkeit/Allgemeinheit
  - Wird für Parent-Propagation Decay verwendet (spezifischere Tags erhalten graduell abnehmende Gewichte für ihre Eltern-Tags)

### System-Konfiguration (Tunable Parameters)

Die folgenden Werte steuern das Verhalten der Suche und können angepasst werden, wenn der User danach fragt:

- **`parent_decay_base`**: `0.6` (Basis für Parent-Propagation Decay - je höher, desto stärker bleiben Parent-Tags gewichtet)
- **`lsh_scale_factor`**: `10` (Gewichtungs-Skalierung für LSH-Shingles - höhere Werte = feinere Gewichtungsabstufungen)
- **`min_tag_weight`**: `0.05` (Minimales Gewicht für Tag-Propagation - Tags mit geringerem Gewicht werden abgeschnitten)
- **`decay_fast`**: `0.1` (Freshness-Decay für schnelllebige Themen mit `veraenderungstempo >= 8`)
- **`decay_medium`**: `0.01` (Freshness-Decay für mittelschnelle Themen mit `veraenderungstempo 4-7`)
- **`decay_slow`**: `0.001` (Freshness-Decay für stabile Themen mit `veraenderungstempo 1-3`)

---

## Kategorien

### Gesundheit

+name:gesundheit
+schlagworte: fitness, wellbeing, körperliche verfassung, health, wohlbefinden, vitalität, medizin, vorsorge, krankheit, genesung
+themen_wichtigkeit:9
+veraenderungstempo:6
+nutzungsfokus:7
+verwandte_kategorien: persoenliche_entwicklung:7, familie_und_beziehungen:6
+beschreibung: Diese Kategorie umfasst körperliche und psychische Gesundheit im Alltag. Hier geht es um Fitness, medizinische Themen, Vorsorge, Krankheitsverläufe, Genesung und allgemeines Wohlbefinden. Inhalte können von Arztbesuchen über Health-Check-ups bis hin zu Tipps für Vitalität, Prävention und gesunden Lebensstil reichen. Notizen, die primär Leistung, Karriere oder Organisation betreffen, gehören eher in Produktivität oder Arbeit und Karriere, nicht hier.

#### Sport

+name:sport
+schlagworte: training, workout, exercise, ausdauer, krafttraining, cardio, bewegung, sportarten, wettkampf
+verwandte_kategorien: reisen_und_freizeit:3
+beschreibung: Sport bündelt alles rund um Training, Workout und regelmäßige körperliche Bewegung. Dazu zählen Ausdauer- und Krafttraining, Cardio, verschiedene Sportarten, Wettkampfvorbereitung und persönliche Trainingspläne. Hier passen auch Reflexionen über Motivation, Fitness-Tracker, Sportequipment oder den Aufbau einer Exercise-Routine. Reine Gesundheitsfragen ohne Bezug zu Bewegung gehören eher in Gesundheit oder Ernährung.

#### Ernährung

+name:ernaehrung
+schlagworte: diät, essen, food, diet, nährstoffe, vitamine, kalorien, mahlzeiten, lebensmittel, gesund essen
+verwandte_kategorien: umwelt_und_nachhaltigkeit/nachhaltiger_lebensstil:5
+beschreibung: Ernährung deckt alles rund ums Essen, Diät, Food und gesundes Essverhalten ab. Typisch sind Fragen zu Nährstoffen, Vitaminen, Kalorien, Mahlzeitenplanung, Lebensmittelauswahl und langfristigen Ernährungsgewohnheiten. Hier landen auch Überlegungen zu Essverhalten, Verdauung, Intoleranzen und wie Ernährung das Wohlbefinden oder die körperliche Verfassung beeinflusst. Finanz- oder Nachhaltigkeitsaspekte von Lebensmitteln sind nur Neben-Aspekte, Hauptfokus ist die Ernährungsqualität.

##### Kochen

+name:kochen
+schlagworte: cooking, cuisine, kochen, kulinarik, rezepte, zubereitung, backen, küchentechniken, zutaten
+verwandte_kategorien: haushalt:7, umwelt_und_nachhaltigkeit/nachhaltiger_lebensstil:4
+beschreibung: Kochen beschreibt die praktische Zubereitung von Speisen im Alltag. Inhalte sind Rezepte, Kochtechniken, Backen, Küchenorganisation, Zutatenwahl, Cuisine-Stile und konkrete Anleitungen Schritt für Schritt. Hier passen auch Notizen zu Küchengeräten, Meal-Prep, kulinarischen Experimenten und Verbesserungen von Koch-Skills. Ernährungsphilosophie oder Diätstrategien ohne direkten Kochbezug gehören eher in Ernährung oder Diäten.

##### Diäten

+name:diaeten
+schlagworte: diets, ernährungspläne, abnehmen, gewichtsreduktion, fasten, low carb, keto, vegan, vegetarisch
+verwandte_kategorien: finanzen_und_investitionen/budgetierung:3
+beschreibung: Diäten umfasst gezielte Ernährungspläne mit Fokus auf Gewichtsreduktion, Körperkomposition oder bestimmte gesundheitliche Ziele. Hier geht es um Abnehmen, Fasten, Low Carb, Keto, vegane oder vegetarische Diets und deren praktische Umsetzung. Notizen können Erfahrungen mit Diätprogrammen, Fortschrittsverfolgung, Cheat Days oder Herausforderungen beim Durchhalten enthalten. Allgemeines Kochen oder Genuss ohne Planungs- und Kontrollfokus gehört eher in Kochen oder Ernährung.

##### Ernährungswissenschaft

+name:ernaehrungswissenschaft
+schlagworte: nutrition science, ernährungsforschung, diätetik, stoffwechsel, biochemie, nahrungsergänzungsmittel
+verwandte_kategorien: lernen_und_bildung:4
+beschreibung: Ernährungswissenschaft behandelt die wissenschaftliche Perspektive auf Nutrition. Dazu zählen Ernährungsforschung, Diätetik, Stoffwechselprozesse, biochemische Hintergründe und evidenzbasierte Empfehlungen. Hier passen Notizen zu Studien, Makro- und Mikronährstoffen, Nahrungsergänzungsmitteln, Laborwerten sowie kritische Bewertungen von Health-Claims. Diese Kategorie ist analytischer und theoriebezogener als alltagspraktische Themen wie Kochen oder Diäten.

#### Schlaf

+name:schlaf
+schlagworte: sleep, schlafqualität, erholung, schlafhygiene, traum, schlaflosigkeit, ruhephasen, regeneration
+verwandte_kategorien: mentale_gesundheit:7, produktivitaet/fokus_und_konzentration:5
+beschreibung: Schlaf umfasst alles rund um Schlafqualität, Erholung und Regeneration. Hier gehören Themen wie Schlafhygiene, Einschlafrituale, Durchschlafprobleme, Träume, Schlaflosigkeit, Müdigkeit und Optimierung der Ruhephasen hin. Notizen können Beobachtungen zu Schlafrhythmus, Tracking-Daten, Auswirkungen von Bildschirmzeit oder Stress auf den Schlaf und Experimente mit Routinen enthalten. Psychische Themen ohne expliziten Bezug zum Schlaf liegen eher bei Mentale Gesundheit.

#### Mentale Gesundheit

+name:mentale_gesundheit
+schlagworte: psychische gesundheit, mental wellbeing, stress management, psychologie, achtsamkeit, therapie, resilienz, burnout-prävention
+verwandte_kategorien: persoenliche_entwicklung/selbstreflexion:8, persoenliche_entwicklung:6
+beschreibung: Mentale Gesundheit deckt psychische Gesundheit, emotionales Wohlbefinden und mental wellbeing ab. Hier geht es um Stress, Depression, Angst, Burnout, Resilienz, Therapieerfahrungen, Achtsamkeit und psychologische Hintergründe. Notizen können sowohl subjektive Zustände und Krisen als auch Tools wie Meditation, Journaling oder therapeutische Methoden beschreiben. Reine Produktivitäts- oder Organisationsfragen ohne emotionalen Bezug gehören nicht hierher.

##### Stressmanagement

+name:stressmanagement
+schlagworte: stress management, entspannungstechniken, coping-strategien, meditation, atemübungen, stressabbau, work-life-balance
+verwandte_kategorien: produktivitaet/fokus_und_konzentration:7, persoenliche_entwicklung/selbstreflexion:6
+beschreibung: Stressmanagement fokussiert auf den konkreten Umgang mit Stress im Alltag. Dazu zählen Entspannungstechniken, Coping-Strategien, Atemübungen, Meditation, Pausenplanung und Work-Life-Balance. Hier passen Notizen über Stressoren, persönliche Trigger, Experimente mit neuen Routinen, Retreats oder Apps zur Stressreduktion. Allgemeine psychische Themen ohne Fokus auf praktische Stressbewältigung gehören eher in Mentale Gesundheit.

#### Arzt und Vorsorge

+name:arzt_und_vorsorge
+schlagworte: doctor, arzt, vorsorge, untersuchung, gesundheit, prävention, impfung, check-up
+verwandte_kategorien: versicherungen:5
+beschreibung: Arzt und Vorsorge umfasst alle Kontakte zu medizinischem Personal sowie präventive Maßnahmen. Hierzu gehören Arztbesuche, Untersuchungen, Check-ups, Impfungen, Screening-Programme, Laborberichte und medizinische Empfehlungen. Notizen können Terminvorbereitung, Fragen an den Doctor, Befunde, Nachsorgepläne und Vorsorgestrategien enthalten. Breitere Lifestyle-Themen ohne konkreten Arzt- oder Präventionsbezug liegen eher in Gesundheit allgemein.

---

### Haushalt

+name:haushalt
+schlagworte: home, domestic, wohnung, hausarbeit, haushaltsführung, wohnen, immobilie, einrichtung
+themen_wichtigkeit:6
+veraenderungstempo:3
+nutzungsfokus:7
+verwandte_kategorien: familie_und_beziehungen/familienmanagement:7, produktivitaet:5, umwelt_und_nachhaltigkeit:4
+beschreibung: Haushalt umfasst das Führen und Organisieren von Wohnung oder Haus. Dazu gehören Hausarbeit, Wohnungsorganisation, Einrichtung, Haushaltsführung, Umgang mit Gegenständen und alltägliche Routinen im Home-Bereich. Notizen können sich auf Putzpläne, Einkaufslisten, Lagerung, Renovierungsplanung, Möbel, Haushaltsgeräte oder generelle Organisation beziehen. Familienspezifische Koordination steht dagegen eher unter Familienmanagement.

#### Reinigung

+name:reinigung
+schlagworte: putzen, sauber machen, hygiene, reinigungsmittel, ordnung halten, frühjahrsputz, wäsche waschen
+verwandte_kategorien: umwelt_und_nachhaltigkeit/abfallmanagement:5
+beschreibung: Reinigung fokussiert auf Putzen, Sauberkeit und Hygiene im Wohnraum. Typische Inhalte sind Putzpläne, Reinigungsmittel, Oberflächenpflege, Badezimmer- und Küchenhygiene, Wäsche waschen und Frühjahrsputz. Hier gehören auch Tipps zu Fleckenentfernung, Aufräumaktionen und Routinen, um Ordnung zu halten. Nachhaltigkeitsthemen wie Zero Waste stehen nur am Rand und gehören primär in Abfallmanagement.

#### Organisation

+name:organisation
+schlagworte: organisation, planung, strukturierung, aufräumen, decluttering, minimalismus, stauraum, ablage
+verwandte_kategorien: produktivitaet/aufgabenverwaltung:7, familie_und_beziehungen/familienmanagement:7
+beschreibung: Organisation im Haushalt betrifft Strukturierung, Aufräumen und Stauraumkonzepte in Wohnung oder Haus. Notizen können Decluttering-Projekte, Minimalismus, Ablagesysteme, Schrankorganisation, Etikettierung und praktische Aufbewahrungsideen enthalten. Der Fokus liegt auf physischer Ordnung und Home-Organisation, nicht auf digitalen Tools oder beruflichen Projekten. Digitale oder arbeitsbezogene Organisation gehört eher in Aufgabenverwaltung oder Wissensverwaltung.

#### Wartung

+name:wartung
+schlagworte: maintenance, reparatur, instandhaltung, heimwerken, renovierung, handwerk, werkzeug, gerätepflege
+verwandte_kategorien: umwelt_und_nachhaltigkeit/abfallmanagement:4, makerspace_und_diy:6
+beschreibung: Wartung umfasst die Instandhaltung von Haus, Wohnung und Geräten. Dazu zählen Reparaturen, Heimwerken, Renovierungsarbeiten, Werkzeugnutzung, Gerätepflege, Wartungsintervalle und Inspektionen. Notizen können Anleitungen, Materiallisten, Projektpläne, Erfahrungsberichte zu Handwerksprojekten oder Kontakte zu Handwerkern enthalten. Kreative DIY-Projekte ohne klaren Instandhaltungsfokus gehören eher in Makerspace und DIY.

---

### Produktivität

+name:produktivitaet
+schlagworte: effizienz, zeitmanagement, organisation, leistung, output, workflow, effektivität, selbstmanagement
+themen_wichtigkeit:8
+veraenderungstempo:5
+nutzungsfokus:8
+verwandte_kategorien: arbeit_und_karriere/arbeitsorganisation:8, lernen_und_bildung/wissensverwaltung:7, technologie_und_programmierung/softwareentwicklung:5
+beschreibung: Produktivität beschreibt Effizienz, Zeitnutzung und Selbstmanagement, um mehr relevanten Output zu erzeugen. Hier geht es um Workflows, Priorisierung, Planung, Fokus, Tools und Methoden für effektiveres Arbeiten und Leben. Notizen können Systeme wie GTD, persönliche Routinen, Experimentberichte, Produktivitäts-Apps, Reviews oder Reflektionen über Leistung enthalten. Reine Wohlfühl- oder Gesundheitsaspekte ohne Leistungsbezug gehören eher zu Gesundheit oder Mentale Gesundheit.

#### Zeitmanagement

+name:zeitmanagement
+schlagworte: time management, terminplanung, priorisierung, kalender, zeitplanung, zeitfresser, deadlines
+verwandte_kategorien: arbeit_und_karriere/arbeitsorganisation:8, behoerden_und_verwaltung/termine_und_fristen:7, familie_und_beziehungen/kindererziehung/kindergarten_und_schule:6
+beschreibung: Zeitmanagement fokussiert darauf, wie Termine, Aufgaben und verfügbare Stunden geplant und genutzt werden. Typische Inhalte sind Kalenderführung, Priorisierung, Time-Blocking, Umgang mit Deadlines, Zeitfresser-Analysen und langfristige Planung. Hier passen Notizen zu Tages- und Wochenplänen, Reviews, Tools wie Kalender-Apps oder Timetracker und Strategien für bessere Balance. Inhalte ohne expliziten Zeitbezug, die nur Organisation oder Inhalte betreffen, gehören eher in Aufgabenverwaltung oder Wissensverwaltung.

#### Aufgabenverwaltung

+name:aufgabenverwaltung
+schlagworte: task management, todo listen, aufgabenplanung, projektmanagement, kanban, gtd, getting things done, backlog
+verwandte_kategorien: haushalt/organisation:7, familie_und_beziehungen/familienmanagement:6
+beschreibung: Aufgabenverwaltung behandelt das Erfassen, Strukturieren und Abarbeiten von Todos und Projekten. Dazu gehören Task-Management-Systeme, Kanban-Boards, Backlogs, Checklisten, Projektstrukturierung und Review-Prozesse. Hier passen Notizen zu Tool-Setups (z. B. Trello, Todoist), eigenen Workflows, Projektstatus, Prioritäten und Reflektionen über Durchsatz. Reine inhaltliche Notizen ohne Task-Charakter gehören eher in Wissensverwaltung oder thematische Kategorien.

#### Fokus und Konzentration

+name:fokus_und_konzentration
+schlagworte: fokus, aufmerksamkeit, konzentrationstechniken, deep work, flow, ablenkungsfrei, pomodoro
+verwandte_kategorien: mentale_gesundheit:6, arbeit_und_karriere:4
+beschreibung: Fokus und Konzentration dreht sich um Deep Work, Aufmerksamkeit und ablenkungsfreies Arbeiten. Typische Inhalte sind Konzentrationstechniken, Flow-Zustände, Pomodoro, Umgang mit Notifications, Fokus-Apps und die Gestaltung einer störungsarmen Umgebung. Notizen können Experimente mit Fokus-Ritualen, Selbstbeobachtung, Erfolgs- und Misserfolgsfaktoren und Strategien zur Reduktion von Multitasking enthalten. Themen, die primär emotionale Belastung betreffen, gehören eher in Mentale Gesundheit oder Stressmanagement.

---

### Lernen und Bildung

+name:lernen_und_bildung
+schlagworte: education, studie, lernen, knowledge, bildungsweg, schule, universität, fortbildung, lebenslanges lernen
+themen_wichtigkeit:8
+veraenderungstempo:4
+nutzungsfokus:6
+verwandte_kategorien: persoenliche_entwicklung:5, technologie_und_programmierung:5, familie_und_beziehungen/kindererziehung/kindergarten_und_schule:7
+beschreibung: Lernen und Bildung umfasst alle Formen von formaler und informeller Education. Hier geht es um Schule, Studium, Weiterbildung, Kurse, Lernstrategien und lebenslanges Lernen. Notizen können persönliche Lernziele, Curricula, Reflexionen über Bildungswege, Vergleich von Programmen sowie Erfahrungen mit Prüfungen und Abschlüssen enthalten. Reine Wissensorganisation ohne Lernkontext gehört eher in Wissensverwaltung.

#### Studientechniken

+name:studientechniken
+schlagworte: lernmethoden, study techniques, memorization, gedächtnistraining, lernplan, prüfungsvorbereitung, notiztechniken
+verwandte_kategorien: lernen_und_bildung/wissensverwaltung:8, produktivitaet/zeitmanagement:5
+beschreibung: Studientechniken fokussieren auf Methoden, wie man effizienter lernt. Dazu zählen Lernmethoden, Memorization-Techniken, Spaced Repetition, Lernpläne, Prüfungsvorbereitung, Notiztechniken und Gedächtnistraining. Hier passen detaillierte Beschreibungen von eigenen Lern-Experimenten, Auswertung von Ergebnissen und Adaptionen klassischer Methoden. Allgemeine Inhalte zu Kursen oder Themen ohne methodischen Fokus gehören eher in Online-Kurse und Ressourcen oder die jeweilige Fachkategorie.

#### Wissensverwaltung

+name:wissensverwaltung
+schlagworte: knowledge management, information organization, pkm, zettelkasten, notizen, wissensdatenbank, archivierung
+verwandte_kategorien: produktivitaet/aufgabenverwaltung:7, technologie_und_programmierung/softwareentwicklung:5, persoenliche_entwicklung/selbstreflexion:6
+beschreibung: Wissensverwaltung behandelt Systeme und Strukturen, um Informationen langfristig nutzbar zu machen. Dazu gehören PKM, Zettelkasten, Notizsysteme, Wissensdatenbanken, Tagging, Archivierung und Retrieval-Strategien. Notizen können Datenbank- oder Markdown-Strukturen, Graph-Ansätze, Tools, Workflows, Import-/Exportstrategien und Evaluierungen von Knowledge-Management-Setups enthalten. Reine Lernziele oder Kursinhalte ohne Systembezug gehören eher in Lernen und Bildung allgemein.

#### Online-Kurse und Ressourcen

+name:online_kurse_und_ressourcen
+schlagworte: e-learning, online education, digitale ressourcen, mooc, tutorials, webinare, zertifikate, udemy, coursera
+verwandte_kategorien: technologie_und_programmierung:7, arbeit_und_karriere/berufliche_weiterentwicklung:7
+beschreibung: Online-Kurse und Ressourcen umfasst E-Learning-Plattformen, digitale Lernmaterialien und webbasierte Tutorials. Hier gehören Notizen zu MOOCs, Udemy-, Coursera- oder YouTube-Kursen, Webinaren, Zertifikatsprogrammen und deren Qualität hin. Inhalte können Kurszusammenfassungen, To-Watch-Listen, Bewertungen, Preis-Leistungs-Einschätzungen und Transfer in die Praxis beschreiben. Allgemeine Lernmethodik ohne Bezug zu konkreten Ressourcen gehört eher in Studientechniken.

---

### Kreativität und Hobbys

+name:kreativitaet_und_hobbys
+schlagworte: creativity, hobbies, freizeitaktivitäten, schöpferisch, basteln, diy, leidenschaft, interessen
+themen_wichtigkeit:7
+veraenderungstempo:4
+nutzungsfokus:7
+verwandte_kategorien: technologie_und_programmierung:6, persoenliche_entwicklung:4
+beschreibung: Kreativität und Hobbys bündelt freizeitbezogene, schöpferische und spielerische Aktivitäten. Dazu zählen künstlerische Projekte, Basteln, DIY, kreative Routinen und persönliche Leidenschaften außerhalb von Arbeit und Pflicht. Notizen können Projektideen, Moodboards, Inspirationssammlungen, Hobby-Logbücher und Reflexionen über kreative Blockaden enthalten. Sobald es stark technisch wird (z. B. Programmierung), gehört der Hauptfokus eher in Technologie und Programmierung.

#### Kunst und Handwerk

+name:kunst_und_handwerk
+schlagworte: art, crafting, malen, zeichnen, skizzieren, töpfern, nähen, design, ästhetik
+verwandte_kategorien: kultur_und_gesellschaft/kunst_und_kulturgeschichte:6
+beschreibung: Kunst und Handwerk umfasst Malen, Zeichnen, Design, Skizzieren, Nähen, Töpfern und andere Crafting-Aktivitäten. Hier passen Anleitungen, Projektideen, Materiallisten, Techniktipps, Stil-Experimente und Reflexionen über ästhetische Entscheidungen. Notizen können auch Ausstellungsbesuche, Portfolio-Planung oder Entwicklung eines eigenen Stils abbilden. Reine Theorie zu Kunstgeschichte gehört eher in Kunst und Kulturgeschichte.

#### Musik

+name:musik
+schlagworte: music, instrumente, komponieren, musiktheorie, gesang, band, orchester, playlist, konzert
+verwandte_kategorien: persoenliche_entwicklung/selbstreflexion:3, soziales_und_gemeinschaft/veranstaltungen_und_treffen:4
+beschreibung: Musik behandelt alles rund um Musikhören, Musikmachen und Musiktheorie. Inhalte sind Instrumentenlernen, Komposition, Gesang, Band- oder Orchestererfahrungen, Playlists, Konzertbesuche und Musikproduktion. Notizen können Übungspläne, Songideen, Harmoniefolgen, Equipment-Fragen und Reflexionen über Musikgeschmack enthalten. Gesellschaftliche Themen rund um Musikszene ohne persönlichen Praxisbezug gehören eher in Kultur und Gesellschaft.

#### Schreiben

+name:schreiben
+schlagworte: writing, kreatives schreiben, literatur, storytelling, blogging, tagebuch, roman, gedichte, autorschaft
+verwandte_kategorien: persoenliche_entwicklung/selbstreflexion:7, kultur_und_gesellschaft:4
+beschreibung: Schreiben umfasst kreatives und reflektierendes Schreiben jenseits von rein formalen Texten. Hier gehören Storytelling, Romane, Kurzgeschichten, Gedichte, Blogging, Tagebuch und Autorschaftsideen hin. Notizen können Plot-Skizzen, Charakterentwürfe, Schreibübungen, Textfragmente, Stil-Experimente und Journaling-Einträge enthalten. Formale Behördenbriefe oder Arbeitsmails liegen eher in Kommunikation mit Behörden bzw. Arbeit und Karriere.

#### Fotografie und Videografie

+name:fotografie_und_videografie
+schlagworte: photography, videography, kamera, bildkomposition, videobearbeitung, lichtsetzung, shooting, portfolio
+verwandte_kategorien: reisen_und_freizeit/aktivitaeten_und_sehenswuerdigkeiten:7, kunst_und_handwerk:4
+beschreibung: Fotografie und Videografie deckt Bildgestaltung, Kameraarbeit und Bewegtbildproduktion ab. Inhalte sind Kamera-Settings, Objektive, Lichtsetzung, Bildkomposition, Videobearbeitung, Schnitt-Workflows, Shooting-Planung und Portfolioaufbau. Notizen können Shooting-Logs, Location-Ideen, Presets, Color-Grading-Notizen und Erfahrungsberichte zu Gear enthalten. Wenn der Fokus primär auf Reisezielen liegt und Bilder nur Nebenprodukt sind, gehört es eher in Aktivitäten und Sehenswürdigkeiten.

#### Makerspace und DIY

+name:makerspace_und_diy
+schlagworte: makerspace, diy, basteln, elektronik, arduino, raspberry pi, prototyping, handwerk
+verwandte_kategorien: technologie_und_programmierung/hardware_und_smart_home:8, technologie_und_programmierung/progrmammiersprachen/bash_shell_scripting:4, umwelt_und_nachhaltigkeit/abfallmanagement:3
+beschreibung: Makerspace und DIY umfasst Bastel- und Bauprojekte mit Technik- oder Handwerksfokus. Dazu zählen Elektronik, Arduino, Raspberry Pi, Prototyping, Löten, Holz- und Metallprojekte, Heimautomation als Bastelprojekt und Experimentieraufbauten. Notizen können Schaltpläne, Bauteillisten, Projektjournale, Fehlersuche und Iterationen dokumentieren. Reine Software ohne physischen Bezug gehört eher in Technologie und Programmierung.

##### 3D-Druck

+name:3d_druck
+schlagworte: 3d-druck, additive fertigung, modellierung, slicer software, filament, drucktechniken, prototyping
+verwandte_kategorien: technologie_und_programmierung/hardware_und_smart_home:5
+beschreibung: 3D-Druck behandelt additive Fertigung und alle Schritte von der Modellierung bis zum fertigen Druck. Inhalte sind CAD-Modelle, Slicer-Software, Filamentwahl, Druckparameter, Kalibrierung, Fehlersuche, Drucktechniken und Nachbearbeitung. Notizen können Projektlogs, Profileinstellungen, Materialtests und Optimierungsschritte enthalten. Allgemeine DIY-Projekte ohne Bezug zu Additive Manufacturing gehören in Makerspace und DIY.

##### Mechanische Tastaturen

+name:mechanische_tastaturen
+schlagworte: mechanische tastaturen, keyboard building, custom keyboards, switches, keycaps, layout design, ergonomie, firmware, qmk, via, zmk
+verwandte_kategorien: technologie_und_programmierung/hardware_und_smart_home:8, technologie_und_programmierung/programmiersprachen:4
+beschreibung: Mechanische Tastaturen umfasst Design, Bau und Nutzung von Custom Keyboards. Hier passen Themen wie Switches, Keycaps, Layout-Design, Ergonomie, Firmware (QMK, VIA, ZMK), Löt- oder Hotswap-Projekte und Modding hin. Notizen können Build-Logs, Layout-Experimente, Keymap-Entwürfe, Teilelisten und Eindrücke zu Tippgefühl oder Sound enthalten. Allgemeine Software-Konfiguration ohne Keyboard-Bezug gehört eher in Technologie und Programmierung.

---

### Technologie und Programmierung

+name:technologie_und_programmierung
+schlagworte: technology, programming, softwareentwicklung, it, computer, digitalisierung, tech, informatik
+themen_wichtigkeit:9
+veraenderungstempo:8
+nutzungsfokus:7
+verwandte_kategorien: produktivitaet:6, kreativitaet_und_hobbys:7, arbeit_und_karriere:5
+beschreibung: Technologie und Programmierung bündelt IT, Softwareentwicklung, Computertechnik und digitale Tools. Hier geht es um Coding, Tech-Trends, Hardware, Betriebssysteme, Infrastruktur und Digitalisierungsfragen. Notizen können Architekturen, Toolvergleiche, Troubleshooting, Setup-Anleitungen und Reflexionen über Technologiewahl enthalten. Reine Produktivitäts- oder Lernmethoden ohne Tech-Fokus gehören (auch wenn Tools genutzt werden) eher in Produktivität oder Lernen und Bildung.

#### Programmiersprachen

+name:programmiersprachen
+schlagworte: coding languages, software languages, syntax, java, c++, rust, go
+verwandte_kategorien: lernen_und_bildung/studientechniken:5, arbeit_und_karriere/berufliche_weiterentwicklung:6
+beschreibung: Programmiersprachen behandelt Syntax, Paradigmen und praktische Nutzung verschiedener Coding-Languages. Inhalte sind Sprachvergleiche, Codebeispiele, Best Practices, Typensysteme, Fehlerbilder und typische Anwendungsfälle (z. B. Java, C++, Rust, Go). Notizen können Snippets, Sprachfeatures, Vor- und Nachteile und Migrationspläne enthalten. Themen, die eher Architektur oder Prozesse betreffen, gehören in Softwareentwicklung.

##### Python

+name:python
+schlagworte: python, programmierung, scripting, datenanalyse, maschinelles lernen, webentwicklung, flask, django
+verwandte_kategorien: technologie_und_programmierung/softwareentwicklung:6
+beschreibung: Python fokussiert auf alles, was konkret mit der Programmiersprache Python zu tun hat. Dazu zählen Skripte, Libraries, Datenanalyse, Machine Learning, Webentwicklung mit Flask oder Django, Automatisierung und Tooling. Notizen können Codebeispiele, Projektideen, Debugging-Logs, Virtual-Env-Setups, Performance-Überlegungen oder Best Practices enthalten. Allgemeine Sprachvergleiche ohne Python-Fokus gehören eher in Programmiersprachen.

##### JavaScript

+name:javascript
+schlagworte: javascript, webentwicklung, frontend, backend, node.js, react, angular, vue.js
+verwandte_kategorien: technologie_und_programmierung/programmiersprachen/typescript:8, technologie_und_programmierung/softwareentwicklung:6
+beschreibung: JavaScript umfasst Frontend- und Backend-Entwicklung mit JS. Inhalte sind DOM-Manipulation, Browser-APIs, Node.js, Frameworks wie React, Angular oder Vue sowie Build-Tooling. Notizen können Komponenten-Design, Event-Handling, Asynchronität, typische Bugs, Architekturentscheidungen und Snippets enthalten. Wenn der Fokus klar auf TypeScript liegt, gehören Inhalte eher in TypeScript, auch wenn JS erwähnt wird.

##### TypeScript

+name:typescript
+schlagworte: typescript, javascript superset, typisierung, webentwicklung, angular, react, vue.js
+verwandte_kategorien: technologie_und_programmierung/programmiersprachen/javascript:8, technologie_und_programmierung/softwareentwicklung:6
+beschreibung: TypeScript behandelt typisiertes JavaScript und seine Nutzung im Webdevelopment. Hier geht es um Typsystem, Interfaces, Generics, Refactoring mit TS, Integration in Frameworks wie React, Angular oder Vue und Build-Konfiguration. Notizen können Migration von JS zu TS, Fehlerdiagnose durch den Compiler, Pattern für saubere Typen und Erfahrungen mit DX enthalten. Reine JS-spezifische Laufzeitthemen ohne Typenbezug gehören eher in JavaScript.

##### Bash/Shell Scripting

+name:bash_shell_scripting
+schlagworte: bash, shell scripting, linux commands, automationsskripte, terminal, cli, systemadministration
+verwandte_kategorien: technologie_und_programmierung/betriebssysteme/linux:8, kreativitaet_und_hobbys/makerspace_und_diy:4
+beschreibung: Bash/Shell Scripting umfasst Skripte und Kommandozeilenarbeit in Unix-/Linux-Umgebungen. Inhalte sind Shell-Befehle, Automationsskripte, Pipe-Workflows, Cronjobs, Systemadministration und CLI-Tools. Notizen können konkrete Skripte, One-Liner, Dotfiles, Debugging-Tipps, Sicherheitsüberlegungen und Best Practices für Shell-Design enthalten. Allgemeine Linux-Administration ohne Skriptfokus gehört eher in Linux.

#### Softwareentwicklung

+name:softwareentwicklung
+schlagworte: software development, software engineering, coding, architektur, design patterns, testing, debugging, version control, ide
+verwandte_kategorien: arbeit_und_karriere/berufliche_weiterentwicklung:7, produktivitaet:5
+beschreibung: Softwareentwicklung deckt den gesamten Software-Engineering-Prozess ab. Dazu gehören Architektur, Design Patterns, Testing, Debugging, Code-Reviews, Versionierung, CI/CD, Ideenausarbeitung und Wartung. Notizen können Projektarchitekturen, Refactoring-Pläne, Qualitätsstrategien, Toolchains und Lessons Learned enthalten. Themen, die primär eine bestimmte Sprache betreffen, gehören in die passende Programmiersprachen-Unterkategorie.

##### Git und Versionierung

+name:git_und_versionierung
+schlagworte: git, version control, quellcodeverwaltung, branches, merges, pull requests, github, gitlab, bitbucket
+verwandte_kategorien: arbeit_und_karriere/berufliche_weiterentwicklung:4
+beschreibung: Git und Versionierung fokussiert auf Versionskontrolle und kollaboratives Arbeiten am Code. Inhalte sind Branching-Modelle, Merges, Rebase, Pull Requests, Workflows auf GitHub/GitLab/Bitbucket und Commit-Strategien. Notizen können Befehlscheatsheets, Hooks, CI-Integration, Release-Management und Fehleranalysen bei Merge-Konflikten enthalten. Allgemeine Projektorganisation ohne Versionsbezug gehört eher in Arbeitsorganisation oder Softwareentwicklung.

#### Technische Trends

+name:technische_trends
+schlagworte: tech trends, innovationen, technologische entwicklung, ki, ai, blockchain, iot, zukunftstechnologien, gadgets
+verwandte_kategorien: kultur_und_gesellschaft/soziale_themen:3
+beschreibung: Technische Trends umfasst neue Technologien, Innovationen und Zukunftsthemen in der Tech-Welt. Dazu zählen KI/AI, Blockchain, IoT, neue Gadgets, Frameworks, Tools und sich abzeichnende Paradigmenwechsel. Notizen können Trendanalysen, erste Experimente, Einschätzungen zu Reifegrad, Chancen/Risiken und mögliche Anwendungsfelder enthalten. Detailierte Implementierungen im Alltag gehören eher in die jeweilige Fachkategorie (z. B. KI in Softwareentwicklung).

#### Cybersecurity

+name:cybersecurity
+schlagworte: cybersecurity, informationssicherheit, datenschutz, netzwerksicherheit, verschlüsselung, firewalls, sicherheitsprotokolle
+verwandte_kategorien: behoerden_und_verwaltung:3, linux:4
+beschreibung: Cybersecurity behandelt Informationssicherheit, Datenschutz und den Schutz von Systemen und Netzwerken. Inhalte sind Verschlüsselung, Authentifizierung, Firewalls, Sicherheitsprotokolle, Härtung von Systemen, Bedrohungsmodelle und Incident Response. Notizen können Security-Checklisten, Konfigurationsbeispiele, Threat-Analysen, Pen-Test-Erkenntnisse und Policy-Überlegungen enthalten. Rechtliche Regelungen ohne technischen Fokus gehören eher in Behörden und Verwaltung.

#### Hardware und Smart Home

+name:hardware_und_smart_home
+schlagworte: hardware, smart home, iot geräte, heimautomatisierung, sensoren, vernetzte geräte, technik im haushalt
+verwandte_kategorien: haushalt:5, umwelt_und_nachhaltigkeit/energieeffizienz:6
+beschreibung: Hardware und Smart Home umfasst physische IT-Geräte und vernetzte Heimautomation. Dazu gehören PCs, Komponenten, Sensoren, Aktoren, IoT-Geräte, smarte Steckdosen, Lichtsteuerungen, Hubs und Integrationen. Notizen können Setups, Verdrahtung, Protokolle (z. B. Zigbee, MQTT), Automationsregeln und Troubleshooting enthalten. Reine Bastelprojekte ohne Smart-Home-Bezug gehören eher in Makerspace und DIY.

#### Betriebssysteme

+name:betriebssysteme
+schlagworte: operating systems, os, windows, macos, systemadministration, installationsanleitungen, konfiguration
+verwandte_kategorien: technologie_und_programmierung/betriebssysteme/linux:7, technologie_und_programmierung/softwareentwicklung:4
+beschreibung: Betriebssysteme behandelt OS-Konzepte, Installation und Konfiguration von Systemen wie Windows und macOS. Inhalte sind Systemsetup, Treiber, Benutzerverwaltung, File-Systeme, Security-Settings und Problembehebung. Notizen können Installationsanleitungen, Tuning-Tipps, Backup-Strategien und Vergleich verschiedener OS-Versionen enthalten. Spezifische Linux-Themen gehören in die Unterkategorie Linux.

##### Linux

+name:linux
+schlagworte: linux, open source, distributions, terminal, shell, paketmanagement, server administration
+verwandte_kategorien: lernen_und_bildung/wissensverwaltung:3
+beschreibung: Linux fokussiert speziell auf Linux-Distributionen und deren Nutzung. Inhalte sind Paketmanagement, Terminal-Nutzung, Dienste, Server-Administration, Desktop-Umgebungen, Shell-Tools und Systemd/Init-Setups. Notizen können Distro-Vergleiche, Config-Dateien, Troubleshooting-Logs, Skripte und Best Practices für Admin-Aufgaben enthalten. Allgemeine Shell-Themen, die mehrere OS betreffen, gehören eher in Bash/Shell Scripting.

---

### Persönliche Entwicklung

+name:persoenliche_entwicklung
+schlagworte: personal development, self improvement, growth, persönlichkeitsentwicklung, selbstoptimierung, mindset, charakter
+themen_wichtigkeit:8
+veraenderungstempo:3
+nutzungsfokus:6
+verwandte_kategorien: gesundheit/mentale_gesundheit:8, familie_und_beziehungen:7, arbeit_und_karriere:5
+beschreibung: Persönliche Entwicklung umfasst Self-Improvement, Growth und langfristige Arbeit an Persönlichkeit und Mindset. Hier geht es um Werte, Gewohnheiten, Charakter, Lebensziele, Identität und innere Haltung. Notizen können Reflexionen, Entwicklungspläne, Coaching-Impulse, Übungen, Buchzusammenfassungen zu Personal Development und Fortschrittslogs enthalten. Reine Therapie- oder Krisenthemen gehören eher in Mentale Gesundheit.

#### Zielsetzung und Motivation

+name:zielsetzung_und_motivation
+schlagworte: goal setting, motivation, selbstmotivation, ziele erreichen, vision, ambition, disziplin, gewohnheiten
+verwandte_kategorien: arbeit_und_karriere:6, produktivitaet:7
+beschreibung: Zielsetzung und Motivation fokussiert auf das Definieren und Erreichen von Zielen. Inhalte sind Visionen, SMART-Ziele, Habit-Building, Disziplin, Motivationstrigger, Rückschläge und Review-Routinen. Notizen können Jahres- und Quartalsziele, Tracking-Tabellen, Belohnungssysteme und Reflexionen über Motivationseinbrüche enthalten. Wenn Ziele primär finanziell oder karrierebezogen sind, können Querverweise zu Finanzen und Investitionen oder Arbeit und Karriere sinnvoll sein.

#### Selbstreflexion

+name:selbstreflexion
+schlagworte: self reflection, introspektion, persönliches wachstum, journaling, selbsterkenntnis, stärken, schwächen, werte
+verwandte_kategorien: kreativitaet_und_hobbys/schreiben:7, familie_und_beziehungen:5, gesundheit/mentale_gesundheit:7
+beschreibung: Selbstreflexion behandelt bewusste Innenschau und Selbsterkenntnis. Hier passen Journaling, Fragen an sich selbst, Auswertung von Erlebnissen, Stärken-/Schwächen-Analysen, Wertearbeit und Identitätsfragen hin. Notizen können Tagebucheinträge, Prompt-Listen, Auswertungen von Gesprächen, Mustererkennung und persönliche Einsichten enthalten. Reines kreatives Schreiben ohne Reflexionsfokus gehört eher in Schreiben.

#### Soziale Fähigkeiten

+name:soziale_faehigkeiten
+schlagworte: social skills, kommunikation, zwischenmenschliche fähigkeiten, empathie, konfliktlösung, verhandlung, rhetorik, charisma
+verwandte_kategorien: soziales_und_gemeinschaft:7, familie_und_beziehungen:7
+beschreibung: Soziale Fähigkeiten umfasst Kommunikation und zwischenmenschliche Skills. Inhalte sind Empathie, aktives Zuhören, Konfliktlösung, Verhandlung, Rhetorik, Smalltalk, Präsenz und Charisma. Notizen können Gesprächsanalysen, Übungspläne, Feedback-Auswertungen, Rollenübungen und Erkenntnisse aus Literatur oder Kursen zu Social Skills enthalten. Themen zu gesellschaftlichen Strukturen ohne persönlichen Skill-Fokus gehören eher in Soziales und Gemeinschaft oder Kultur und Gesellschaft.

---

### Reisen und Freizeit

+name:reisen_und_freizeit
+schlagworte: travel, urlaub, freizeit, abenteuer, tourismus, erholung, ausflüge, weltenbummler
+themen_wichtigkeit:6
+veraenderungstempo:5
+nutzungsfokus:5
+verwandte_kategorien: familie_und_beziehungen:4, gesundheit/sport:3, kreativitaet_und_hobbys/fotografie_und_videografie:6
+beschreibung: Reisen und Freizeit bündelt Aktivitäten außerhalb von Arbeit und Pflicht mit Reise- oder Urlaubsbezug. Dazu gehören Urlaubsplanung, Ausflüge, Abenteuer, Tourismus, Erholung und Weltenbummeln. Notizen können Reiseideen, Bucket-Lists, Erfahrungsberichte, Kostenübersichten und Nachbereitungen vergangener Trips enthalten. Lokale Hobbys ohne Reisebezug gehören eher in Kreativität und Hobbys oder Soziales und Gemeinschaft.

#### Reiseplanung

+name:reiseplanung
+schlagworte: trip planning, urlaubsplanung, reiseroute, buchung, packliste, reisevorbereitung, visum, impfungen
+verwandte_kategorien: finanzen_und_investitionen/budgetierung:7, familie_und_beziehungen/familienmanagement:6
+beschreibung: Reiseplanung fokussiert auf die Vorbereitung und Organisation von Trips. Inhalte sind Reiserouten, Buchungen, Packlisten, Visa, Impfungen, Budgetplanung und Risikoabwägungen. Notizen können konkrete Pläne, Checklisten, Vergleichstabellen, Zeitpläne und alternative Optionen enthalten. Allgemeine Erfahrungsberichte ohne Planungsaspekt gehören eher in Aktivitäten und Sehenswürdigkeiten.

#### Unterkünfte und Transport

+name:unterkuenfte_und_transport
+schlagworte: accommodations, lodging, transportation, hotel, hostel, airbnb, flug, zug, mietwagen, logistik
+verwandte_kategorien: finanzen_und_investitionen/budgetierung:4
+beschreibung: Unterkünfte und Transport behandelt die praktische Logistik einer Reise. Dazu zählen Hotels, Hostels, Airbnb, Züge, Flüge, Mietwagen, ÖPNV und Transfers. Notizen können Preisvergleiche, Buchungsdaten, Erfahrungsberichte zu Anbietern, Sitzplatz- oder Zimmerpräferenzen und Tipps zur Anreise enthalten. Strategische Gesamtplanung des Urlaubs gehört eher in Reiseplanung.

#### Aktivitäten und Sehenswürdigkeiten

+name:aktivitaeten_und_sehenswuerdigkeiten
+schlagworte: activities, sightseeing, freizeitaktivitäten, touren, museen, wandern, kultur erleben, attraktionen
+verwandte_kategorien: kultur_und_gesellschaft:5, kreativitaet_und_hobbys/fotografie_und_videografie:7
+beschreibung: Aktivitäten und Sehenswürdigkeiten umfasst das, was man vor Ort unternimmt. Inhalte sind Sightseeing, Touren, Museen, Wandern, Kulturangebote, Freizeitparks, besondere Orte und lokale Erfahrungen. Notizen können Must-See-Listen, Tagespläne, Bewertungen von Attraktionen, Kinderfreundlichkeit und persönliche Highlights enthalten. Wenn es primär um Fotografie- oder Videoprojekte der Reise geht, gehört der Schwerpunkt in Fotografie und Videografie.

---

### Finanzen und Investitionen

+name:finanzen_und_investitionen
+schlagworte: finance, money management, investing, geld, vermögen, reichtum, finanzielle freiheit, ökonomie
+themen_wichtigkeit:8
+veraenderungstempo:6
+nutzungsfokus:7
+verwandte_kategorien: arbeit_und_karriere:7, behoerden_und_verwaltung/bankangelegenheiten:8
+beschreibung: Finanzen und Investitionen deckt Geldmanagement, Vermögensaufbau und wirtschaftliche Entscheidungen ab. Inhalte sind Budgetierung, Sparen, Investieren, finanzielle Freiheit, Risiko, Ökonomie und persönliche Finanzstrategie. Notizen können Kontenübersichten, Entscheidungslogs, Portfolio-Überlegungen, Szenarienrechnungen und finanzielle Ziele enthalten. Reine Steuer- oder Behördenformalia gehören eher in Steuern bzw. Behörden und Verwaltung.

#### Budgetierung

+name:budgetierung
+schlagworte: budgeting, haushaltsplanung, finanzplanung, ausgabenkontrolle, sparquote, haushaltsbuch, kosten senken
+verwandte_kategorien: haushalt:7, familie_und_beziehungen/familienmanagement:7
+beschreibung: Budgetierung fokussiert auf Haushaltsplanung und Ausgabenkontrolle. Inhalte sind Budgets, Kategorien, Haushaltsbücher, Sparquoten, Kostenreduktion, Cashflow und Regel-Setups für Ausgaben. Notizen können Monatsabschlüsse, Plan-Ist-Vergleiche, Sparziele, Budget-Templates und Regelanpassungen enthalten. Themen zum Investieren oder langfristigem Vermögensaufbau gehören eher in Sparen und Investieren.

#### Sparen und Investieren

+name:sparen_und_investieren
+schlagworte: saving, investing, anlegen, aktien, etf, fonds, immobilien, krypto, zinsen, dividenden, altersvorsorge
+verwandte_kategorien: arbeit_und_karriere:5, umwelt_und_nachhaltigkeit:3
+beschreibung: Sparen und Investieren umfasst den Aufbau von Vermögen durch Rücklagen und Anlageentscheidungen. Inhalte sind Sparkonten, Aktien, ETFs, Fonds, Immobilien, Krypto, Zinsen, Dividenden und Altersvorsorge. Notizen können Strategien, Risikoprofile, Kauf-/Verkaufsentscheidungen, Portfolio-Reviews und Lessons Learned aus Marktbewegungen enthalten. Reines Ausgabenmanagement ohne Anlagefokus gehört eher in Budgetierung.

#### Schuldenmanagement

+name:schuldenmanagement
+schlagworte: debt management, schuldenabbau, kreditmanagement, umschuldung, tilgung, zinslast, insolvenzvermeidung
+verwandte_kategorien: behoerden_und_verwaltung:5
+beschreibung: Schuldenmanagement behandelt den Umgang mit bestehenden Verbindlichkeiten. Inhalte sind Kredite, Ratenzahlungen, Umschuldung, Tilgungspläne, Zinslast, Verhandlungen mit Gläubigern und Strategien zur Schuldenreduktion. Notizen können Tilgungspläne, Status-Updates, Alternativszenarien und persönliche Reflexionen zu Ursachen und Verhalten enthalten. Allgemeine Spar- oder Investitionsüberlegungen ohne Schuldenbezug gehören in Sparen und Investieren.

#### Steuern

+name:steuern
+schlagworte: taxes, steuererklärung, steuerplanung, absetzbarkeit, steuervorteile, finanzamt, steuerrecht, einkommensteuer
+verwandte_kategorien: behoerden_und_verwaltung:8, arbeit_und_karriere:4
+beschreibung: Steuern umfasst Steuererklärung, Steuerplanung und Interaktion mit dem Finanzamt. Inhalte sind absetzbare Ausgaben, Steuervorteile, Steuerrecht, Fristen, ELSTER, Belege und Kommunikation mit Behörden zum Thema taxes. Notizen können Checklisten, Fallbeispiele, Vorbereitungsunterlagen, Rückfragen an Steuerberater und Auswertungen von Bescheiden enthalten. Allgemeine Finanzplanung ohne Steuerfokus gehört eher in Finanzen und Investitionen.

---

### Umwelt und Nachhaltigkeit

+name:umwelt_und_nachhaltigkeit
+schlagworte: environment, sustainability, umweltschutz, ökologie, klimawandel, naturschutz, ressourcen
+themen_wichtigkeit:7
+veraenderungstempo:5
+nutzungsfokus:5
+verwandte_kategorien: haushalt:4, reisen_und_freizeit:3
+beschreibung: Umwelt und Nachhaltigkeit bündelt Themen rund um Ökologie, Klimawandel, Ressourcenschonung und umweltbewusstes Leben. Inhalte sind Umweltschutz, Naturschutz, CO₂-Fußabdruck, Konsumkritik und gesellschaftliche Nachhaltigkeitsdebatten. Notizen können persönliche Strategien, Projektideen, politische Einschätzungen und Alltagsanpassungen enthalten. Wenn der Fokus auf konkreten Haushaltspraktiken liegt, kann die Zuordnung zu Energieeffizienz oder Abfallmanagement sinnvoller sein.

#### Energieeffizienz

+name:energieeffizienz
+schlagworte: energy efficiency, energieeinsparung, ressourcenschonung, strom sparen, heizkosten, dämmung, erneuerbare energien, solar
+verwandte_kategorien: technologie_und_programmierung/hardware_und_smart_home:6, finanzen_und_investitionen/budgetierung:4
+beschreibung: Energieeffizienz fokussiert auf das Senken von Energieverbrauch und Kosten. Inhalte sind Stromsparen, Heizkosten, Dämmung, erneuerbare Energien, Solar, intelligente Steuerung und Effizienzklassen von Geräten. Notizen können Verbrauchsprotokolle, Umbaupläne, Amortisationsrechnungen, Hardwareauswahl und Optimierungsideen enthalten. Allgemeine Nachhaltigkeitsdiskussionen ohne Energiebezug gehören eher in Umwelt und Nachhaltigkeit.

#### Abfallmanagement

+name:abfallmanagement
+schlagworte: waste management, recycling, mülltrennung, kompostierung, upcycling, zero waste, plastikvermeidung
+verwandte_kategorien: haushalt/reinigung:5, kreativitaet_und_hobbys/makerspace_und_diy:4
+beschreibung: Abfallmanagement behandelt den Umgang mit Müll, Recycling und Vermeidung. Inhalte sind Mülltrennung, Kompostierung, Upcycling, Zero-Waste-Ansätze, Plastikvermeidung und lokale Entsorgungsregeln. Notizen können Sortierregeln, Projektideen zum Wiederverwenden, Erfahrungsberichte mit Sammelsystemen und Optimierungen im Alltag enthalten. Kreative Bastelprojekte mit Fokus auf Upcycling können auch mit Makerspace und DIY verknüpft sein.

#### Nachhaltiger Lebensstil

+name:nachhaltiger_lebensstil
+schlagworte: sustainable living, umweltbewusst leben, grüner lifestyle, bio, fairtrade, regional, saisonal, konsumverzicht
+verwandte_kategorien: gesundheit/ernaehrung:5, finanzen_und_investitionen/sparen_und_investieren:3
+beschreibung: Nachhaltiger Lebensstil umfasst praktische Entscheidungen für ein umweltbewusstes Leben. Inhalte sind grüner Lifestyle, Bio-Produkte, Fairtrade, regionaler und saisonaler Konsum, Konsumverzicht, Second Hand und Mobilitätsentscheidungen. Notizen können Selbstverpflichtungen, Challenges, Einkaufsleitlinien, Reflexionen über Konsumgewohnheiten und Erfahrungsberichte enthalten. Streng finanzielle Optimierung ohne Umweltfokus gehört eher in Sparen und Investieren oder Budgetierung.

---

### Soziales und Gemeinschaft

+name:soziales_und_gemeinschaft
+schlagworte: social, community, gemeinschaft, gesellschaft, zusammenleben, integration, inklusion, bürgerschaft
+themen_wichtigkeit:6
+veraenderungstempo:4
+nutzungsfokus:4
+verwandte_kategorien: familie_und_beziehungen:6, kultur_und_gesellschaft:7, persoenliche_entwicklung/soziale_faehigkeiten:8
+beschreibung: Soziales und Gemeinschaft behandelt das Zusammenleben von Menschen in Gruppen, Nachbarschaften und Gesellschaft. Inhalte sind Community-Building, Integration, Inklusion, Vereine, Initiativen und bürgerschaftliches Engagement. Notizen können Projektideen, Erfahrungen mit Gruppen, lokale Initiativen, Reflexionen über Zugehörigkeit und soziale Dynamiken enthalten. Persönliche Skill-Entwicklung in Kommunikation gehört eher in Soziale Fähigkeiten.

#### Freiwilligenarbeit

+name:freiwilligenarbeit
+schlagworte: volunteering, ehrenamtliche tätigkeit, gemeinnützige arbeit, engagement, spende, hilfsorganisation, sozialarbeit
+verwandte_kategorien: kultur_und_gesellschaft/soziale_themen:7, persoenliche_entwicklung:5
+beschreibung: Freiwilligenarbeit fokussiert auf ehrenamtliches Engagement und gemeinnützige Arbeit. Inhalte sind Tätigkeiten bei Hilfsorganisationen, Vereinen, NGOs, Spendenaktionen, Mentoring und lokale Projekte. Notizen können Einsatzberichte, Motivation, Zeitplanung, Organisationsstrukturen, Impact-Reflexionen und Ideen für neue Engagementformen enthalten. Allgemeine sozialpolitische Debatten ohne konkretes eigenes Engagement gehören eher in Soziale Themen.

#### Veranstaltungen und Treffen

+name:veranstaltungen_und_treffen
+schlagworte: events, meetups, soziale veranstaltungen, partys, feiern, konferenzen, workshops, stammtisch
+verwandte_kategorien: soziales_und_gemeinschaft/netzwerken:7, kreativitaet_und_hobbys/musik:4
+beschreibung: Veranstaltungen und Treffen umfasst Events mit sozialem Charakter. Inhalte sind Partys, Feiern, Meetups, Konferenzen, Workshops, Stammtische und Community-Treffen. Notizen können Event-Ideen, Agenda-Entwürfe, Teilnehmerlisten, Nachberichte, Feedback und Learnings enthalten. Wenn der Fokus auf fachlichem Inhalt eines Events liegt (z. B. Tech-Konferenz), gehört dieser eher in die passende Themenkategorie.

#### Netzwerken

+name:netzwerken
+schlagworte: networking, kontakte knüpfen, beziehungen aufbauen, karrierenetzwerk, linkedin, visitenkarten, smalltalk
+verwandte_kategorien: arbeit_und_karriere:7, persoenliche_entwicklung/soziale_faehigkeiten:7
+beschreibung: Netzwerken behandelt das gezielte Knüpfen und Pflegen von Kontakten zu beruflichen oder thematischen Zwecken. Inhalte sind Karrierenetzwerke, LinkedIn-Strategien, Visitenkarten, Follow-up-Mails, Elevator Pitches und Beziehungsmanagement. Notizen können Kontaktlisten, Gesprächsnotizen, Networking-Ziele, Eventstrategien und Nachverfolgung enthalten. Reine Freundschafts- oder Familienbeziehungen gehören eher in Familie und Beziehungen.

---

### Arbeit und Karriere

+name:arbeit_und_karriere
+schlagworte: work, career, beruf, job, arbeitswelt, profession, laufbahn, erfolg
+themen_wichtigkeit:8
+veraenderungstempo:5
+nutzungsfokus:7
+verwandte_kategorien: produktivitaet:7, finanzen_und_investitionen:7, persoenliche_entwicklung:5
+beschreibung: Arbeit und Karriere umfasst berufliches Leben, Jobwahl, Laufbahn und Entwicklung im Arbeitskontext. Inhalte sind Berufsfelder, Jobzufriedenheit, Arbeitgeberwahl, Karriereziele, Rollenwechsel und Arbeitsbedingungen. Notizen können Lebenslauf-Ideen, Jobtagebuch, Entscheidungen, Gehaltsüberlegungen und langfristige Karrierestrategien enthalten. Reine Task- oder Zeitplanung ohne Karrierekontext gehört eher in Produktivität.

#### Jobsuchen und Bewerbungen

+name:jobsuchen_und_bewerbungen
+schlagworte: job search, bewerbung, karrierewechsel, lebenslauf, anschreiben, vorstellungsgespräch, stellenanzeigen, headhunter
+verwandte_kategorien: persoenliche_entwicklung/zielsetzung_und_motivation:6, soziales_und_gemeinschaft/netzwerken:7
+beschreibung: Jobsuchen und Bewerbungen fokussiert auf den Prozess, einen neuen Job zu finden. Inhalte sind Stellensuche, Lebenslauf, Anschreiben, Interviewvorbereitung, Assessment-Center, Headhunter und Bewerbungsstrategien. Notizen können Rollenprofile, individuelle Bewerbungen, Fragenkataloge, Feedback aus Gesprächen und Entscheidungslogbücher enthalten. Allgemeine Karriereentwicklung ohne konkreten Bewerbungsprozess gehört eher in Berufliche Weiterentwicklung.

#### Berufliche Weiterentwicklung

+name:berufliche_weiterentwicklung
+schlagworte: professional development, karriereentwicklung, weiterbildung, beförderung, gehaltsverhandlung, skills, qualifikation
+verwandte_kategorien: lernen_und_bildung/online_kurse_und_ressourcen:7, technologie_und_programmierung/softwareentwicklung:5
+beschreibung: Berufliche Weiterentwicklung behandelt Wachstum innerhalb oder zwischen Berufen. Inhalte sind Weiterbildung, Skill-Aufbau, Beförderung, Rollenwechsel, Gehaltsverhandlungen, Mentoring und langfristige Karriereplanung. Notizen können Entwicklungspläne, Kursauswahl, Feedbackgespräche, Jahresziele und Evaluierungen von Fortschritten enthalten. Reine fachliche Inhalte (z. B. neue Programmiersprache) gehören in die entsprechende Fachkategorie.

#### Arbeitsorganisation

+name:arbeitsorganisation
+schlagworte: work organization, arbeitsplatzmanagement, workflow optimierung, büroorganisation, ablage, schreibtisch, home office
+verwandte_kategorien: produktivitaet/zeitmanagement:8, produktivitaet/aufgabenverwaltung:7
+beschreibung: Arbeitsorganisation umfasst Strukturierung und Gestaltung der Arbeitssituation. Inhalte sind Arbeitsplatzgestaltung, Homeoffice-Setup, Ablage im Büro, Prozessoptimierung, Workflow-Design und Teamorganisation. Notizen können To-Desk-Layouts, Dateiablagesysteme, Büroregeln, Meeting-Strukturen und Verbesserungsideen enthalten. Allgemeine persönliche Produktivität ohne klaren Arbeitskontext gehört eher in Produktivität.

---

### Behörden und Verwaltung

+name:behoerden_und_verwaltung
+schlagworte: administration, bürokratie, amtliche angelegenheiten, formulare, anträge, gesetze, vorschriften
+themen_wichtigkeit:8
+veraenderungstempo:7
+nutzungsfokus:9
+verwandte_kategorien: finanzen_und_investitionen:6, arbeit_und_karriere:5, familie_und_beziehungen:4
+beschreibung: Behörden und Verwaltung behandelt amtliche Angelegenheiten, Bürokratie und gesetzliche Vorschriften. Inhalte sind Formulare, Anträge, Meldungen, amtliche Bescheide, Fristen und grundlegende Verwaltungsprozesse. Notizen können Checklisten für Anträge, Gesprächsnotizen von Ämtern, benötigte Unterlagen und eigene Ablaufpläne enthalten. Finanzspezifische Themen ohne Behördenkontakt gehören eher in Finanzen und Investitionen.

#### Termine und Fristen

+name:termine_und_fristen
+schlagworte: deadlines, termine, fristen, wiedervorlage, kalender, erinnerungen, steuertermine, abgabefristen
+verwandte_kategorien: produktivitaet/zeitmanagement:8, familie_und_beziehungen/familienmanagement:5
+beschreibung: Termine und Fristen fokussiert auf zeitkritische Verwaltungs- und Pflichttermine. Inhalte sind Abgabefristen, Steuertermine, Wiedervorlagen, Erinnerungen und Kalenderorganisation für amtliche oder formale Vorgänge. Notizen können Fristenlisten, Reminder-Setups, Wiederholrhythmen und Zusammenstellungen aller wichtigen Termine enthalten. Allgemeine Zeitplanung ohne Behörden- oder Pflichtbezug gehört eher in Zeitmanagement.

#### Kommunikation mit Behörden

+name:kommunikation_mit_behoerden
+schlagworte: communication with authorities, behördenkontakt, amtliche kommunikation, schriftverkehr, widerspruch, bescheid, bürgeramt
+verwandte_kategorien: kreativitaet_und_hobbys/schreiben:2, behoerden_und_verwaltung/versicherungen:5
+beschreibung: Kommunikation mit Behörden umfasst schriftlichen und mündlichen Austausch mit Ämtern und öffentlichen Institutionen. Inhalte sind Anschreiben, Widersprüche, Nachfragen zu Bescheiden, Formulierungen, Telefonnotizen und Gesprächsvorbereitung. Notizen können Briefentwürfe, Gesprächsleitfäden, Protokolle, Eskalationsstufen und Dokumentation von Ergebnissen enthalten. Kreatives oder persönliches Schreiben ohne Amtsbezug gehört eher in Schreiben.

#### Bankangelegenheiten

+name:bankangelegenheiten
+schlagworte: banking, bankangelegenheiten, kontoführung, überweisungen, kreditkarten, online banking, finanzverwaltung
+verwandte_kategorien: finanzen_und_investitionen:9
+beschreibung: Bankangelegenheiten behandelt den operativen Umgang mit Banken. Inhalte sind Kontoführung, Überweisungen, Kreditkarten, Kreditanträge, Dispo, Online Banking, Authentifizierungsverfahren und Gebühren. Notizen können Kontenübersichten, Gespräche mit Bankberatern, Konditionsvergleiche und Einrichtung von Daueraufträgen enthalten. Strategische Finanzplanung und Investments gehören eher in Finanzen und Investitionen.

#### Versicherungen

+name:versicherungen
+schlagworte: insurance, versicherungen, police, schadensfälle, prämien, versicherungsarten, verträge, kündigung
+verwandte_kategorien: finanzen_und_investitionen:7, familie_und_beziehungen:4
+beschreibung: Versicherungen umfasst Auswahl, Verwaltung und Nutzung von Versicherungsverträgen. Inhalte sind Policen, Tarife, Deckungsumfang, Schadensfälle, Risikoabwägungen, Kündigungen und Neuabschlüsse. Notizen können Vertragsübersichten, Leistungsfälle, Vergleichsnotizen, Beratungsergebnisse und eigene Kriterien für Versicherungsentscheidungen enthalten. Allgemeine finanzielle Rücklagen ohne Versicherungsbezug gehören eher in Sparen und Investieren.

---

### Kultur und Gesellschaft

+name:kultur_und_gesellschaft
+schlagworte: culture, society, gesellschaft, zivilisation, tradition, bräuche, werte, normen
+themen_wichtigkeit:6
+veraenderungstempo:5
+nutzungsfokus:3
+verwandte_kategorien: soziales_und_gemeinschaft:7, reisen_und_freizeit/aktivitaeten_und_sehenswuerdigkeiten:4
+beschreibung: Kultur und Gesellschaft bündelt Themen rund um Werte, Normen, Traditionen und das Funktionieren von Gesellschaften. Inhalte sind Kulturgeschichte, Bräuche, Medien, Popkultur, soziale Strukturen und gesellschaftliche Diskurse. Notizen können Beobachtungen, Analysen, Lese- oder Filmnotizen, Diskussionen und eigene Positionierungen enthalten. Persönliche Beziehungsfragen ohne gesellschaftliche Ebene gehören eher in Familie und Beziehungen.

#### Kunst und Kulturgeschichte

+name:kunst_und_kulturgeschichte
+schlagworte: art, culture history, kunstgeschichte, epochen, museen, ausstellungen, kulturerbe, architektur
+verwandte_kategorien: kreativitaet_und_hobbys/kunst_und_handwerk:6, kreativitaet_und_hobbys/fotografie_und_videografie:4
+beschreibung: Kunst und Kulturgeschichte behandelt historische und theoretische Aspekte von Kunst und Kultur. Inhalte sind Epochen, Stile, Künstler, Museen, Ausstellungen, Architektur und Kulturerbe. Notizen können Zusammenfassungen, Museumsbesuche, Werkinterpretationen, Stilvergleiche und Lektürenotizen enthalten. Eigene künstlerische Praxis gehört eher in Kunst und Handwerk.

#### Soziale Themen

+name:soziale_themen
+schlagworte: social issues, gesellschaftliche themen, sozialwissenschaften, gerechtigkeit, gleichberechtigung, armut, bildungspolitik
+verwandte_kategorien: soziales_und_gemeinschaft/freiwilligenarbeit:7, persoenliche_entwicklung/soziale_faehigkeiten:4
+beschreibung: Soziale Themen umfasst gesellschaftliche Fragestellungen und Social Issues. Inhalte sind Gerechtigkeit, Gleichberechtigung, Armut, Bildungspolitik, Diskriminierung, Migration und Sozialwissenschaften. Notizen können Artikelzusammenfassungen, Meinungsbilder, Debattenargumente, Policy-Vorschläge und Reflexionen über strukturelle Probleme enthalten. Persönliche Skills in Konfliktlösung gehören eher in Soziale Fähigkeiten.

#### Internationale Beziehungen

+name:internationale_beziehungen
+schlagworte: international relations, außenpolitik, geopolitik, diplomatie, welthandel, globalisierung, krieg und frieden, uno
+verwandte_kategorien: kultur_und_gesellschaft/soziale_themen:5
+beschreibung: Internationale Beziehungen behandelt Außenpolitik, Geopolitik und globale Verflechtungen. Inhalte sind Diplomatie, Welthandel, Allianzen, Konflikte, Krieg und Frieden, UN-Politik und internationale Organisationen. Notizen können Länderanalysen, Ereignisprotokolle, Strategieüberlegungen, Szenarien und historische Vergleiche enthalten. Persönliche Reiseerlebnisse gehören eher in Reisen und Freizeit.

---

### Familie und Beziehungen

+name:familie_und_beziehungen
+schlagworte: family, relationships, familie, beziehungen, verwandtschaft, freundschaft, liebe, bindung
+themen_wichtigkeit:9
+veraenderungstempo:3
+nutzungsfokus:7
+verwandte_kategorien: gesundheit:6, persoenliche_entwicklung:7, haushalt:5
+beschreibung: Familie und Beziehungen umfasst familiäre Strukturen, Partnerschaften, Freundschaften und enge Bindungen. Inhalte sind Familienleben, Rollen, Konflikte, Nähe, Liebe, Verbundenheit und gemeinsamer Alltag. Notizen können Erziehungsfragen, Alltagssituationen, Beziehungsgespräche, Rituale, Sorgen und schöne Momente enthalten. Berufliche Kontakte ohne Privatheitsgrad gehören eher in Netzwerken.

#### Elternsein

+name:elternsein
+schlagworte: parenting, elternschaft, kindererziehung, pädagogik, entwicklung, schule, betreuung, familienleben
+verwandte_kategorien: persoenliche_entwicklung/selbstreflexion:5
+beschreibung: Elternsein behandelt das Leben als Mutter/Vater oder Bezugsperson. Inhalte sind Elternrolle, Rollenverteilung, Belastungen, Freude, Vereinbarkeit, pädagogische Überlegungen und allgemeine Entwicklung der Kinder. Notizen können Alltagsbeispiele, Reflexionen über eigenes Verhalten, Bedürfnisse der Kinder, organisatorische Herausforderungen und emotionale Themen enthalten. Konkrete institutionelle Themen wie Schulverwaltung gehören eher in Kindergarten und Schule oder Behörden und Verwaltung.

##### Kindererziehung

+name:kindererziehung
+schlagworte: kindererziehung, erziehungsstile, disziplin, förderung, kindliche entwicklung, eltern-kind-beziehung
+verwandte_kategorien: persoenliche_entwicklung/selbstreflexion:6, gesundheit/mentale_gesundheit:4
+beschreibung: Kindererziehung fokussiert auf Erziehungsstile, Regeln, Förderung und Beziehungsgestaltung mit Kindern. Inhalte sind Disziplin, Grenzen, Bindung, kindliche Entwicklung, Mediennutzung, Konflikte und pädagogische Strategien. Notizen können konkrete Situationen, Reflexionen, Vereinbarungen, Konsequenzen und Ideen zur Unterstützung der Kinder enthalten. Administrative Themen rund um Einrichtungen gehören eher in Kindergarten und Schule.

##### Kindergarten und Schule

+name:kindergarten_und_schule
+schlagworte: kindergarten, schule, bildungseinrichtungen, vorschule, grundschule, weiterführende schule, schulwahl
+verwandte_kategorien: lernen_und_bildung:7, behoerden_und_verwaltung:4
+beschreibung: Kindergarten und Schule behandelt Bildungs- und Betreuungsinstitutionen für Kinder. Inhalte sind Auswahl von Einrichtungen, Eingewöhnung, Kommunikation mit Pädagogen, Schulwahl, Hausaufgaben, Elternabende und organisatorische Themen. Notizen können Protokolle, To-dos, Infobriefe, Terminübersichten und Entwicklungsrückmeldungen enthalten. Grundsätzliche Erziehungsfragen ohne Institutsbezug gehören eher in Kindererziehung.

#### Partnerschaft

+name:partnerschaft
+schlagworte: partnership, beziehung, ehe, paartherapie, romantik, dating, zusammenleben, kommunikation
+verwandte_kategorien: persoenliche_entwicklung/soziale_faehigkeiten:6, persoenliche_entwicklung/selbstreflexion:5
+beschreibung: Partnerschaft umfasst romantische Beziehungen und Ehe. Inhalte sind Kommunikation, Intimität, Alltagsaufteilung, Streitkultur, Paartherapie, Trennungsgedanken, Romantik und gemeinsame Ziele. Notizen können Gesprächsprotokolle, Wünsche, Bedürfnisse, Musteranalysen, Vereinbarungen und Paarrituale enthalten. Rein sexuelle Themen ohne Beziehungsfokus wären eine eigene Kategorie und gehören nicht automatisch hierher.

#### Familienmanagement

+name:familienmanagement
+schlagworte: family management, familienorganisation, haushaltsführung, familienkalender, aufgabenverteilung, familienbudget
+verwandte_kategorien: haushalt:8, produktivitaet/aufgabenverwaltung:6, reisen_und_freizeit/reiseplanung:6
+beschreibung: Familienmanagement behandelt die Organisation des Familienalltags. Inhalte sind Aufgabenverteilung, Familienkalender, Routinen, Einkaufs- und To-do-Listen, Budgetplanung für die Familie und Koordination von Terminen. Notizen können Wochenpläne, Verantwortlichkeitsübersichten, Checklisten und Review-Runden enthalten. Rein haushaltsbezogene Themen ohne Familienkoordination gehören eher in Haushalt.
