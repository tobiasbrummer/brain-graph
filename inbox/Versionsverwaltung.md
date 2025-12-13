# [Versionsverwaltung](https://de.wikipedia.org/wiki/Versionsverwaltung)
+id:01KCA7EFP1VGQDBHK87GQ0AA5Z

## Summary

Eine Versionsverwaltung ist ein System, das zur Erfassung von Änderungen an Dokumenten oder [Datei](https://de.wikipedia.org/wiki/Datei)en verwendet wird. Alle Versionen werden in einem Archiv mit [Zeitstempel](https://de.wikipedia.org/wiki/Zeitstempel) und Benutzerkennung gesichert und können später wiederhergestellt werden. Versionsverwaltungssysteme werden typischerweise in der Softwareentwicklung eingesetzt, um [Quelltext](https://de.wikipedia.org/wiki/Quelltext)e zu verwalten. Versionsverwaltung kommt auch bei [Büroanwendung](https://de.wikipedia.org/wiki/Office-Paket)en oder [Content-Management-System](https://de.wikipedia.org/wiki/Content-Management-System)en zum Einsatz.

Ein Beispiel ist die [Protokollierung](https://de.wikipedia.org/wiki/Protokoll_(Niederschrift)) in vielen [Wiki](https://de.wikipedia.org/wiki/Wiki)s: hier erzeugt die Software nach jeder Änderung eines Artikels eine neue Version. Alle Versionen bilden eine Kette, in der die jeweils letzte Version gültig ist; es sind meist keine Varianten vorgesehen. Da zu jedem Versionswechsel die grundlegenden Angaben wie Verfasser und Uhrzeit festgehalten werden, kann genau nachvollzogen werden, wer wann was geändert hat. Bei Bedarf – beispielsweise bei versehentlichen Änderungen – kann man zu einer früheren Version zurückkehren.
Die Versionsverwaltung ist eine Form des [Variantenmanagement](https://de.wikipedia.org/wiki/Variantenmanagement)s; dort sind verschiedene Sprachvarianten oder modal auch anders bestimmte Varianten möglich. Für Versionsverwaltungssysteme ist die Abkürzung VCS (Version Control System) gebräuchlich.

## Hauptaufgaben

[Protokollierung](https://de.wikipedia.org/wiki/Protokoll_(Niederschrift))en der Änderungen: Es kann jederzeit nachvollzogen werden, wer wann was geändert hat.

Wiederherstellung von alten Ständen einzelner [Datei](https://de.wikipedia.org/wiki/Datei)en: Somit können versehentliche Änderungen jederzeit wieder rückgängig gemacht werden.

Archivierung der einzelnen Stände eines Projektes: Dadurch ist es jederzeit möglich, auf alle Versionen zuzugreifen.

Koordinierung des gemeinsamen Zugriffs von mehreren Entwicklern auf die [Datei](https://de.wikipedia.org/wiki/Datei)en.

Gleichzeitige Entwicklung mehrerer [Entwicklungszweig](https://de.wikipedia.org/wiki/Abspaltung_(Softwareentwicklung))e (engl. Branch) eines Projektes, was nicht mit der Abspaltung eines anderen Projekts (engl. Fork) verwechselt werden darf.

## Terminologie

Ein Branch, zu deutsch Zweig, ist eine Verzweigung zu einer neuen Version, so dass unterschiedliche Versionen parallel im selben Projekt weiterentwickelt werden können. Änderungen können dabei von einem Branch auch wieder in einen anderen einfließen, was als Merging, zu deutsch verschmelzen, bezeichnet wird. Oft wird der Hauptentwicklungszweig als Trunk (z. B. bei Subversion) oder Main (ehemals Master) (z. B. bei [Git](https://de.wikipedia.org/wiki/Git)) bezeichnet. Branches können zum Beispiel für neue Hauptversionen einer Software erstellt werden oder für [Entwicklungszweig](https://de.wikipedia.org/wiki/Abspaltung_(Softwareentwicklung))e für unterschiedliche Betriebssysteme oder aber auch, um experimentelle Versionen zu erproben. Wird ein Zweig in einer neuen, unabhängigen Versionsverwaltung erstellt, spricht man von einem Fork. Ein bestimmter Stand kann auch mit einem Tag (einem frei wählbaren Bezeichner) gekennzeichnet werden.

## Funktionsweise

Damit die eingesetzten Programme wie z. B. [Texteditor](https://de.wikipedia.org/wiki/Texteditor)en oder [Compiler](https://de.wikipedia.org/wiki/Compiler) mit den im [Repository](https://de.wikipedia.org/wiki/Repository) (engl. Behälter, Aufbewahrungsort) abgelegten [Datei](https://de.wikipedia.org/wiki/Datei)en arbeiten können, ist es erforderlich, dass jeder Entwickler sich den aktuellen (oder einen älteren) Stand des Projektes in Form eines Verzeichnisbaumes aus herkömmlichen [Datei](https://de.wikipedia.org/wiki/Datei)en erzeugen kann. Ein solcher Verzeichnisbaum wird als Arbeitskopie bezeichnet. Ein wichtiger Teil des Versionsverwaltungssystems ist ein Programm, das in der Lage ist, diese Arbeitskopie mit den Daten des [Repository](https://de.wikipedia.org/wiki/Repository)s zu synchronisieren. Das Übertragen einer Version aus dem [Repository](https://de.wikipedia.org/wiki/Repository) in die Arbeitskopie wird als Checkout, Aus-Checken oder Aktualisieren bezeichnet, während die umgekehrte Übertragung Check-in, Einchecken oder Commit genannt wird. Solche Programme werden entweder kommandozeilenorientiert, mit grafischer Benutzeroberfläche oder als Plugin für integrierte Softwareentwicklungsumgebungen ausgeführt. Häufig werden mehrere dieser verschiedenen Zugriffsmöglichkeiten wahlweise bereitgestellt.
Es gibt drei Arten der Versionsverwaltung, die älteste funktioniert lokal, also nur auf einem Computer, die nächste Generation funktionierte mit einem zentralen Archiv und die neueste Generation arbeitet verteilt, also ohne zentrales Archiv. Allen gemein ist, dass die Versionsverwaltungssoftware dabei üblicherweise nur die Unterschiede zwischen zwei Versionen speichert, um Speicherplatz zu sparen. Die meisten Systeme verwenden hierfür ein eigenes [[Datei](https://de.wikipedia.org/wiki/Datei)format](https://de.wikipedia.org/wiki/[Datei](https://de.wikipedia.org/wiki/Datei)format) oder eine [Datenbank](https://de.wikipedia.org/wiki/Datenbank). Dadurch kann eine große Zahl von Versionen archiviert werden. Durch dieses Speicherformat kann jedoch nur mit der Software des Versionsverwaltungssystems auf die Daten zugegriffen werden, die die gewünschte Version bei einem Abruf unmittelbar aus den archivierten Versionen rekonstruiert.

### Lokale Versionsverwaltung

Bei der lokalen Versionsverwaltung wird oft nur eine einzige [Datei](https://de.wikipedia.org/wiki/Datei) versioniert, diese Variante wurde mit Werkzeugen wie SCCS und RCS umgesetzt. Sie findet auch heute noch Verwendung in [Büroanwendung](https://de.wikipedia.org/wiki/Office-Paket)en, die Versionen eines Dokumentes in der [Datei](https://de.wikipedia.org/wiki/Datei) des Dokuments selbst speichern. Auch in technischen Zeichnungen werden Versionen zum Beispiel durch einen [Änderungsindex](https://de.wikipedia.org/wiki/%C3%84nderungsindex) verwaltet.

### Zentrale Versionsverwaltung

Diese Art ist als [Client-Server-System](https://de.wikipedia.org/wiki/Client-Server-Modell) aufgebaut, sodass der Zugriff auf ein [Repository](https://de.wikipedia.org/wiki/Repository) auch über Netzwerk erfolgen kann. Durch eine Rechteverwaltung wird dafür gesorgt, dass nur berechtigte Personen neue Versionen in das Archiv legen können. Die Versionsgeschichte ist hierbei nur im [Repository](https://de.wikipedia.org/wiki/Repository) vorhanden. Dieses Konzept wurde vom Open-Source-Projekt [Concurrent Versions System](https://de.wikipedia.org/wiki/Concurrent_Versions_System) (CVS) populär gemacht, mit Subversion (SVN) neu implementiert und von vielen kommerziellen Anbietern verwendet.

### Verteilte Versionsverwaltung

Die verteilte Versionsverwaltung (DVCS, distributed VCS) verwendet kein zentrales [Repository](https://de.wikipedia.org/wiki/Repository) mehr. Jeder, der an dem verwalteten Projekt arbeitet, hat sein eigenes [Repository](https://de.wikipedia.org/wiki/Repository) und kann dieses mit jedem beliebigen anderen [Repository](https://de.wikipedia.org/wiki/Repository) abgleichen. Die Versionsgeschichte ist dadurch genauso verteilt. Änderungen können lokal verfolgt werden, ohne eine Verbindung zu einem Server aufbauen zu müssen.
Im Gegensatz zur zentralen Versionsverwaltung kommt es nicht zu einem Konflikt, wenn mehrere Benutzer dieselbe Version einer [Datei](https://de.wikipedia.org/wiki/Datei) ändern. Die sich widersprechenden Versionen existieren zunächst parallel und können weiter geändert werden. Sie können später in eine neue Version zusammengeführt werden. Dadurch entsteht ein gerichteter azyklischer Graph ([Polyhierarchie](https://de.wikipedia.org/wiki/Polyhierarchie)) anstatt einer Kette von Versionen. In der Praxis werden bei der Verwendung in der Softwareentwicklung meist einzelne Features oder Gruppen von Features in separaten Versionen entwickelt und diese bei größeren Projekten von Personen mit einer Integrator-Rolle überprüft und zusammengeführt.

Systembedingt bieten verteilte Versionsverwaltungen keine Locks. Da wegen der höheren Zugriffsgeschwindigkeit die Granularität der gespeicherten Änderungen viel kleiner sein kann, können sie sehr leistungsfähige, weitgehend automatische [Merge](https://de.wikipedia.org/wiki/Merge)-Mechanismen zur Verfügung stellen.
Eine Unterart der Versionsverwaltung bieten einfachere Patchverwaltungssysteme, die Änderungen nur in eine Richtung in Produktivsysteme einspeisen.

Obwohl konzeptionell nicht unbedingt notwendig, existiert in verteilten Versionsverwaltungsszenarien üblicherweise ein offizielles [Repository](https://de.wikipedia.org/wiki/Repository). Das offizielle [Repository](https://de.wikipedia.org/wiki/Repository) wird von neuen Projektbeteiligten zu Beginn ihrer Arbeit geklont, d. h. auf das lokale System kopiert.

## Konzepte



### Lock Modify Write

Diese Arbeitsweise eines Versionsverwaltungssystems wird auch als Lock Modify Unlock bezeichnet. Die zugrunde liegende Philosophie wird pessimistische Versionsverwaltung genannt. Einzelne [Datei](https://de.wikipedia.org/wiki/Datei)en müssen vor einer Änderung durch den Benutzer gesperrt und nach Abschluss der Änderung wieder freigegeben werden. Während sie gesperrt sind, verhindert das System Änderungen durch andere Benutzer. Der Vorteil dieses Konzeptes ist, dass kein Zusammenführen von Versionen erforderlich ist, da nur immer ein Entwickler eine [Datei](https://de.wikipedia.org/wiki/Datei) ändern kann. Der Nachteil ist, dass man unter Umständen auf die Freigabe eines Dokuments warten muss, um eine eigene Änderung einzubringen. Binärdateien (im Gegensatz zu [Quelltext](https://de.wikipedia.org/wiki/Quelltext)dateien) erfordern in der Regel diese Arbeitsweise, da das Versionsverwaltungssystem verteilte Änderungen nicht automatisch synchronisieren kann.
Ältester Vertreter dieser Arbeitsweise ist das [Revision Control System](https://de.wikipedia.org/wiki/Revision_Control_System), ebenso bekannt ist [Visual SourceSafe](https://de.wikipedia.org/wiki/Visual_SourceSafe).

Verteilte Versionsverwaltungssysteme kennen systembedingt diese Arbeitsweise nicht.

### Copy Modify [Merge](https://de.wikipedia.org/wiki/Merge)

Ein solches System lässt gleichzeitige Änderungen durch mehrere Benutzer an einer [Datei](https://de.wikipedia.org/wiki/Datei) zu. Anschließend werden diese Änderungen automatisch oder manuell zusammengeführt ([Merge](https://de.wikipedia.org/wiki/Merge)). Somit wird die Arbeit des Entwicklers wesentlich erleichtert, da Änderungen nicht im Voraus angekündigt werden müssen. Insbesondere wenn viele Entwickler räumlich getrennt arbeiten, wie es beispielsweise bei Open-Source-Projekten häufig der Fall ist, ermöglicht dies erst effizientes Arbeiten, da kein direkter Kontakt zwischen den Entwicklern benötigt wird. Problematisch bei diesem System sind Binärdateien, da diese oft nicht automatisch zusammengeführt werden können, sofern kein passendes Werkzeug verfügbar ist. Manche Vertreter dieser Gattung unterstützen daher auch alternativ das Lock-Modify-Write-Konzept für bestimmte [Datei](https://de.wikipedia.org/wiki/Datei)en.
Die zugrunde liegende Philosophie wird als optimistische Versionsverwaltung bezeichnet und wurde entwickelt, um die Schwächen der pessimistischen Versionsverwaltung zu beheben. Alle modernen zentralen und verteilten Systeme setzen dieses Verfahren um.

## Objekt-basierte Versionierung

Über die Grenze des abspeichernden Mediums, der [Datei](https://de.wikipedia.org/wiki/Datei), hinaus geht die Objekt-basierte Versionierung. Objekte werden in der Informatik als sogenannte Instanzen, also Ausprägungen eines Schemas, erzeugt. Auch diese können versioniert gespeichert werden. Die Versionsverwaltung, welche die unterschiedlichen Objektversionen abspeichert, muss mit den entsprechenden Objekttypen umgehen können. Aus dem Grund liest ein solches System nicht allein die [Datei](https://de.wikipedia.org/wiki/Datei) und überprüft diese auf Veränderungen, sondern kann die darin enthaltene [Semantik](https://de.wikipedia.org/wiki/Semantik) interpretieren. Üblicherweise werden Objekte dann nicht dateibasiert, sondern in einer [Datenbank](https://de.wikipedia.org/wiki/Datenbank) abgespeichert. [Produktdatenmanagement](https://de.wikipedia.org/wiki/Produktdatenmanagement)-Systeme (PDM-Systeme) verwalten ihre Daten nach diesem Prinzip.

## Beispiele

Die folgende Tabelle enthält einige Versionsverwaltungssysteme als Beispiele für die verschiedenen Ausprägungsarten.

## Siehe auch

[Versionsnummer](https://de.wikipedia.org/wiki/Versionsnummer)
[Versionshinweise](https://de.wikipedia.org/wiki/Versionshinweise)
[Source Code Control System](https://de.wikipedia.org/wiki/Source_Code_Control_System)
[Dokumentenmanagement](https://de.wikipedia.org/wiki/Dokumentenmanagement)
[Logdatei](https://de.wikipedia.org/wiki/Logdatei)

## Weblinks

Vergleich von SVN, [Git](https://de.wikipedia.org/wiki/Git), [Mercurial](https://de.wikipedia.org/wiki/Mercurial) und CVS (englisch)
Liste von Versionverwaltungssystemen speziell für Linux (englisch, 2004)
Versionskontrollsysteme in der Softwareentwicklung (2005; PDF; 790 kB)
Verteilte Versionskontrollsysteme (2009), CRE
Einführung in Verteilte Versionsverwaltung (englisch)
Semantic Versioning

## References

- http://linuxmafia.com/faq/Apps/vcs.html
- http://betterexplained.com/articles/intro-to-distributed-version-control-illustrated/
- http://www.gesis.org/fileadmin/upload/forschung/publikationen/gesis_reihen/iz_arbeitsberichte/ab_36.pdf
- http://biz30.timedoctor.com/git-mecurial-and-cvs-comparison-of-svn-software/
- https://cre.fm/cre130-verteilte-versionskontrollsysteme
- https://d-nb.info/gnd/4202033-5
- https://semver.org/lang/de/
- https://swb.bsz-bw.de/DB=2.104/SET=1/TTL=1/CMD?retrace=0&trm_old=&ACT=SRCHA&IKT=2999&SRT=RLV&TRM=4202033-5
- https://lobid.org/gnd/4202033-5
- https://prometheus.lmu.de/gnd/4202033-5
- https://explore.gnd.network/gnd/4202033-5

## URL

https://de.wikipedia.org/wiki/Versionsverwaltung

