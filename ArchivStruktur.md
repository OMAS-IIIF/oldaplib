# Archivstruktur für OLDAP / Salsah 2.0

## Status und Zweck dieses Dokuments

Dieses Dokument ist das gemeinsame Arbeitsdokument für die Architektur und die inkrementelle Entwicklung der
Archivfunktionen von OLDAP. Es hält Zielbild, Leitentscheidungen, offene Fragen und geplante Entwicklungsschritte fest.

Architekturpunkte gelten erst dann als verbindlich, wenn sie im Abschnitt
[Entscheidungsstand](#entscheidungsstand) ausdrücklich als **beschlossen** markiert sind. Vorschläge bleiben bis zu ihrer
Bestätigung vorläufig. Offene Punkte stehen im Abschnitt [Offene Fragen](#offene-fragen). Das Dokument wird mit den
praktischen Erfahrungen aus den ersten Anwendungsfällen weiterentwickelt.

## Zielbild

OLDAP soll drei Aufgaben auf einer gemeinsamen Infrastruktur integrieren:

1. **Zugang:** Kulturhistorische Bestände sollen einem breiten Publikum mit einer einfach bedienbaren Suche und einer
   attraktiven Darstellung zugänglich gemacht werden.
2. **Vermittlung und Kontextualisierung:** Archivgut soll beispielsweise in Geschichten, Ausstellungen und thematische
   Zusammenstellungen eingebunden werden können.
3. **Archivische Verwaltung:** Archivgut soll nach archivischen Prinzipien geordnet, beschrieben und verwaltet werden
   können.

Das Fasnachtsprojekt zeigt bereits wesentliche Aspekte des öffentlichen Zugangs und der Kontextualisierung. Die
archivische Verwaltung soll nun schrittweise ergänzt werden, ohne die bestehenden Modelle unnötig zu verkomplizieren.

## Technische Randbedingungen

- Die Lösung basiert auf der bestehenden OLDAP-Plattform.
- GraphDB bleibt das RDF-Backend; Datenmodelle werden mit OLDAP-Ontologien und SHACL beschrieben.
- Bestehende Ontologien, `oldaplib` und `oldap-api` werden rückwärtskompatibel erweitert.
- Der Mediaserver und IIIF bleiben für die Bereitstellung digitaler Repräsentationen zuständig.
- Alle relevanten Medientypen sollen unterstützt werden.
- Die Implementierung soll einfach, nachvollziehbar und inkrementell bleiben.

## Fachlicher Ausgangspunkt

Klassische Archivordnungen verwenden typischerweise mehrere Beschreibungsebenen. Für OLDAP sind insbesondere
folgende Begriffe relevant:

- Bestandsgruppe
- Bestand
- Teilbestand
- Serie
- Teilserie
- Dossier/Akte
- Dokument/Einzelstück

Nicht jedes Archiv verwendet alle Ebenen. Auch zusätzliche Zwischenebenen und direkte Sprünge zwischen Ebenen kommen
in der Praxis vor. Die Hierarchie soll deshalb den archivischen Kontext ausdrücken, aber nicht auf eine einzige starre
Abfolge festgelegt werden.

Der internationale Standard ISAD(G) beschreibt eine mehrstufige, vom Allgemeinen zum Spezifischen verlaufende
Beschreibung. Sein dargestelltes Hierarchiemodell ist ein typischer Fall und keine vollständige Aufzählung aller
zulässigen Kombinationen. Records in Contexts (RiC) bietet ein moderneres und umfassenderes Linked-Data-Modell. RiC
soll zunächst als fachlicher Referenz- und späterer Interoperabilitätsstandard dienen, nicht als vollständiges internes
OLDAP-Datenmodell.

## Architekturprinzipien

### 1. Eine generische Archiveinheit statt vieler Unterklassen

Alle Knoten der archivischen Hierarchie werden durch eine gemeinsame ResourceClass dargestellt, vorläufig
`shared:ArchiveUnit` genannt. Ob eine Einheit eine Bestandsgruppe, ein Bestand, eine Serie oder ein Dossier ist, wird
durch die Eigenschaft `shared:archiveLevel` ausgedrückt.

Die Archivstufe ist damit eine Eigenschaft der Archiveinheit und keine eigene ResourceClass. Dadurch bleiben Modell,
CRUD-Verhalten und Benutzeroberfläche einheitlich. Projekt- oder ebenenspezifische Unterklassen werden erst eingeführt,
wenn ein konkreter Anwendungsfall eigenständiges Verhalten oder deutlich andere Metadaten erfordert.

### 2. Ein einfacher Baum als struktureller Kern

Eine Archiveinheit verweist optional auf genau eine direkt übergeordnete Archiveinheit. Damit entsteht eine einfache
Adjazenzliste:

```text
Bestandsgruppe
└── Bestand
    ├── Serie
    │   └── Dossier
    │       └── Dokument
    └── Dossier
```

Der Baum bildet ausschliesslich die archivische Ordnung ab. Thematische, biografische, ereignisbezogene und andere
Beziehungen werden als separate Verknüpfungen modelliert und dürfen die Archivhierarchie nicht verändern.

### 3. Kontrollierte Werte statt Text-Tags

`archiveLevel` soll auf kontrollierte RDF-Ressourcen mit stabilen IRIs und mehrsprachigen Bezeichnungen verweisen,
nicht auf frei eingegebene Zeichenketten. Als initiale Werte sind vorgesehen:

- `shared:ArchiveGroup`
- `shared:Fonds`
- `shared:Subfonds`
- `shared:Series`
- `shared:Subseries`
- `shared:File`
- `shared:Item`

Die endgültigen Namen und die Frage, ob projektspezifische Erweiterungen erlaubt werden, sind noch offen.

### 4. Archivische Beschreibung und digitale Repräsentation bleiben getrennt

Eine `ArchiveUnit` beschreibt eine intellektuelle archivische Einheit. Ein `shared:MediaObject` beschreibt eine digitale
Datei oder Medienrepräsentation. Beide Konzepte dürfen nicht gleichgesetzt werden:

```text
ArchiveUnit "Protokoll vom 3. Mai"
├── MediaObject "Seite 1.tif"
├── MediaObject "Seite 2.tif"
└── MediaObject "Lesefassung.pdf"
```

Eine Archiveinheit kann ohne Digitalisierung existieren und mehrere Medienobjekte besitzen. Umgekehrt bleiben technische
Medienmetadaten Aufgabe von `MediaObject` und des Mediaservers.

### 5. Staging ist Vorbild, aber nicht Teil der Archivhierarchie

Die bestehende Struktur aus `shared:StagingFolder` und `shared:inStagingFolder` zeigt, dass eine einfache
Elternreferenz in OLDAP funktioniert. Die Staging-Klassen sollen jedoch weder wiederverwendet noch als Oberklassen der
Archivstruktur verwendet werden:

- Staging ist ein temporärer Ingest- und Bearbeitungsprozess.
- Die Archivhierarchie ist die dauerhafte intellektuelle Ordnung.
- Die Publikation aus dem Staging kann Archiveinheiten und ihre Medienverknüpfungen erzeugen oder aktualisieren.

Auch `OldapListNode` ist keine geeignete technische Grundlage. Hierarchische Listen sind kontrollierte Vokabulare mit
eigenem Indexmodell; Archiveinheiten sind reguläre, berechtigte und beschreibbare OLDAP-Ressourcen, die verschoben und
mit anderen Ressourcen verknüpft werden können.

### 6. Wenige harte Regeln im Grundmodell

Das Basismodell soll nur Regeln erzwingen, die für jede Archivstruktur gelten und für die Datenintegrität erforderlich
sind:

- Jede Archiveinheit hat eine Archivstufe und einen Titel.
- Eine Archiveinheit hat höchstens eine direkt übergeordnete Archiveinheit.
- Wurzeleinheiten haben keine übergeordnete Einheit.
- Beim Verschieben dürfen keine Zyklen entstehen.
- Eine optionale Reihenfolge unter Geschwistern muss eindeutig interpretierbar sein.

Folgende Regeln werden vorerst bewusst **nicht** im SHACL-Grundmodell erzwungen:

- Mindestanzahl von Kindern
- eine feste Abfolge der Archivstufen
- XOR-Regeln für unterschiedliche Arten von Untereinheiten
- das Verbot, einzelne Ebenen zu überspringen

Leere Einheiten müssen während der inkrementellen Erfassung zulässig sein. Strengere fachliche Regeln können später
als konfigurierbares Archivprofil, Anwendungsvalidierung oder Warnung in der Benutzeroberfläche ergänzt werden.

## Minimaler Modellvorschlag

Die Namen sind vorläufig und werden vor der Ontologieimplementierung geprüft.

| Element | Kardinalität im MVP | Zweck |
|---|---:|---|
| `shared:ArchiveUnit` | – | Gemeinsame ResourceClass aller archivischen Beschreibungseinheiten |
| `schema:name` oder `dcterms:title` | genau 1 | Menschenlesbarer Titel; Wahl der bestehenden OLDAP-Konvention ist offen |
| `shared:archiveLevel` | genau 1 | Kontrollierte Archivstufe |
| `shared:parentArchiveUnit` | 0..1 | Direkte hierarchische Elternbeziehung |
| `shared:referenceCode` | 0..1 | Archivsignatur oder Referenzcode |
| `shared:hasMediaObject` | 0..n | Verknüpfung zu digitalen Repräsentationen |
| `shared:archiveOrder` | 0..1 | Optionale manuelle Reihenfolge unter Geschwistern |
| `dcterms:description` oder projektspezifische Beschreibung | 0..1/mehrsprachig | Kurze Inhaltsbeschreibung |

Für die erste Version werden keine spezialisierten Python-Klassen benötigt, sofern die generischen
`ResourceInstance`-Funktionen Erstellen, Lesen, Aktualisieren, Löschen und Suchen ausreichend abdecken.

## Inkrementelle Entwicklungsstrategie

Jede Phase soll einen eigenständig nutzbaren vertikalen Schnitt liefern. Der nächste Schritt beginnt erst, wenn der
vorherige mit realistischen Daten erprobt wurde.

### Phase 0: Fachliches Beispiel und Entscheidungen

- Einen kleinen, realen Fasnacht-Bestand mit ungefähr 15–30 Einheiten als Referenzbaum festhalten.
- Die Begriffe und erforderlichen Minimalfelder mit Archivfachpersonen prüfen.
- Die offenen MVP-Fragen in diesem Dokument entscheiden.
- Akzeptanzkriterien und erwartete Abfragen anhand des Beispielbaums formulieren.

**Ergebnis:** Ein gemeinsames fachliches Beispiel und ein entscheidungsreifer MVP-Umfang; noch keine produktive
Implementierung.

### Phase 1: Ontologie-MVP

- `ArchiveUnit`, Elternbeziehung, Archivstufe und minimale Metadaten in der Shared-Ontologie definieren.
- Kontrollierte Archivstufen als benannte RDF-Individuen anlegen.
- Beispieldaten und Ontologie-/SHACL-Tests ergänzen.
- Generische CRUD- und Suchoperationen mit dem Referenzbaum prüfen.
- Noch keine besondere Archiv-API und keine konfigurierbaren Hierarchieregeln einführen.

**Ergebnis:** Archivbäume können mit bestehenden OLDAP-Mitteln gespeichert und gelesen werden.

### Phase 2: Minimale Baumoperationen

- Direkte Kinder und den Pfad zur Wurzel laden.
- Einen Teilbaum für Navigation und Darstellung abfragen.
- Archiveinheiten verschieben und dabei Zyklen verhindern.
- Falls erforderlich, Geschwister manuell sortieren.
- Erst jetzt beurteilen, ob eine kleine Archiv-Servicegrenze in `oldaplib` oder `oldap-api` einen konkreten Nutzen hat.

**Ergebnis:** Die Struktur kann sicher und komfortabel navigiert und bearbeitet werden.

### Phase 3: Archivische Erschliessungsmetadaten

Nur nachgewiesen benötigte Felder werden ergänzt, beispielsweise:

- Laufzeit beziehungsweise Datumsbereich
- Umfang und Medium
- Bestandsbildner und Provenienz
- Inhalt und innere Ordnung
- Zugangs- und Benutzungsbedingungen
- physischer Standort

Gemeinsame Informationen sollen auf der höchsten passenden Ebene beschrieben und nicht unnötig in allen Kindern
dupliziert werden.

**Ergebnis:** Die Struktur unterstützt eine praktisch ausreichende archivische Erschliessung.

### Phase 4: Vermittlung und Kontextualisierung

- Geschichten, Ausstellungen, Themen und Ereignisse mit Archiveinheiten verknüpfen.
- Mehrfachverwendung derselben Archiveinheit in unterschiedlichen Kontexten erlauben.
- Archivische Ordnung und kuratierte Navigation getrennt darstellen.

**Ergebnis:** Publikumszugang und Vermittlung nutzen dieselben Ressourcen, ohne die Archivordnung zu verfälschen.

### Phase 5: Interoperabilität und strengere Profile

- Bedarf für Import/Export oder Mapping zu RiC-O, ISAD(G), EAD oder lokalen Standards bewerten.
- Bei konkretem Bedarf konfigurierbare Hierarchieprofile und zusätzliche Validierungen einführen.
- Berechtigungsvererbung, Massenoperationen und weitergehende Optimierungen nur anhand realer Anforderungen umsetzen.

**Ergebnis:** Erweiterte Standards und Regeln werden ergänzt, ohne das einfache Kernmodell zu belasten.

## Bewusst vertagte Themen

Folgende Funktionen gehören nicht zum ersten MVP:

- vollständige Abbildung von RiC-O
- frei konfigurierbare Archivstufen und Regelmatrizen
- automatische Vererbung aller Metadaten
- automatische Vererbung von OLDAP-Berechtigungen
- komplexe Signaturgeneratoren
- Massenverschiebungen und Massenerschliessung
- physische Magazin-, Behältnis- und Standortverwaltung
- Langzeitarchivierungs- und Aufbewahrungsworkflows
- eine eigene Python-Domänenklasse ohne nachgewiesenen Bedarf

Diese Punkte sind nicht grundsätzlich ausgeschlossen. Sie werden erst aufgenommen, wenn ein konkreter Anwendungsfall
ihren zusätzlichen Modell- und Implementierungsaufwand rechtfertigt.

## Offene Fragen

### Für Phase 0 beziehungsweise vor dem Ontologie-MVP

1. **Bedeutung der Bestandsgruppe:** Ist sie eine vollwertige beschreibbare Archiveinheit oder nur eine
   Navigationsüberschrift beziehungsweise Gruppierung?
2. **Wurzelmodell:** Darf ein OLDAP-Projekt mehrere unabhängige Archivbäume besitzen? Benötigen diese eine eigene
   Ressource wie `Archive` oder genügen mehrere `ArchiveUnit`-Wurzeln?
3. **Archivstufen:** Reichen die initial vorgeschlagenen sieben Stufen? Werden projektspezifische Stufen bereits im MVP
   benötigt?
4. **Signatur:** Ist `referenceCode` für jede Archiveinheit verpflichtend? Wird die Signatur manuell eingegeben,
   automatisch erzeugt oder teilweise aus der Hierarchie abgeleitet?
5. **Titel:** Soll der Titel genau einsprachig oder als `LangString` mehrsprachig sein? Welche bestehende
   Titel-Eigenschaft soll OLDAP konsequent verwenden?
6. **Reihenfolge:** Reicht eine Sortierung nach Signatur oder Titel, oder muss eine davon unabhängige manuelle Ordnung
   gespeichert werden?
7. **Dokumentbegriff:** Bezeichnet `Item`/Dokument die kleinste intellektuell beschriebene Einheit, ein physisches
   Objekt oder beides? Wie werden mehrteilige Dokumente abgegrenzt?
8. **Medienbeziehung:** Kann ein Medienobjekt mehreren Archiveinheiten zugeordnet sein, oder gehört es fachlich genau
   zu einer Einheit?

### Vor Phase 2

9. **Verschieben:** Welche Auswirkungen hat das Verschieben auf Signaturen, Sortierung, Berechtigungen und publizierte
   Links?
10. **Löschen:** Darf eine Archiveinheit mit Kindern gelöscht werden? Wahrscheinlich sollte dies verhindert oder als
    explizite Massenoperation behandelt werden.
11. **Abfrageumfang:** Welche Baumansichten werden wirklich benötigt: direkte Kinder, vollständiger Teilbaum,
    Vorfahrenpfad, Geschwister oder alle davon?
12. **Berechtigungen:** Bleiben Berechtigungen zunächst unabhängig pro Archiveinheit? Falls später Vererbung gewünscht
    wird: Gilt sie nur als Auswertungsregel oder werden Berechtigungen auf Kinder kopiert?

### Vor Phase 3 und später

13. **Pflichtmetadaten:** Welche ISAD(G)-Kernelemente müssen bereits beim Erfassen vorhanden sein, und welche dürfen
    erst vor einer Publikation verlangt werden?
14. **Provenienz:** Werden Bestandsbildner als bestehende Personen-/Organisationen-Ressourcen verknüpft, und kann eine
    Einheit mehrere Bestandsbildner besitzen?
15. **Physische Ordnung:** Muss die physische Lagerstruktur unabhängig von der intellektuellen Archivordnung modelliert
    werden?
16. **Vererbung in der Anzeige:** Welche Metadaten einer übergeordneten Einheit sollen Kinder in der Oberfläche
    kontextuell anzeigen, ohne diese Daten zu duplizieren?
17. **Staging-Publikation:** Erzeugt der Publikationsprozess neue Archiveinheiten, ordnet er Medien bestehenden Einheiten
    zu oder muss er beide Varianten unterstützen?
18. **Standardaustausch:** Welche konkreten Austauschformate oder Zielsysteme haben Priorität? Ohne benannten
    Austauschpartner soll kein komplexes Mapping implementiert werden.

## Entscheidungsstand

### Vorgeschlagene Leitentscheidungen – noch zu bestätigen

- Eine generische `ArchiveUnit` bildet alle Hierarchieebenen ab.
- Die Archivstufe wird als kontrollierte Eigenschaft und nicht durch Unterklassen modelliert.
- Die Hierarchie verwendet eine einfache Elternreferenz mit höchstens einem Elternknoten.
- Archiveinheiten und Medienobjekte sind getrennte Konzepte und werden explizit verknüpft.
- Staging und dauerhafte Archivordnung bleiben getrennte Subsysteme.
- Das Grundmodell erzwingt keine starre Abfolge oder Mindestanzahl von Kindern.
- Erweiterte Regeln, Standards und Services werden inkrementell anhand konkreter Anwendungsfälle eingeführt.

### Noch nicht entschieden

Alle nummerierten Punkte im Abschnitt [Offene Fragen](#offene-fragen), insbesondere Wurzelmodell, Signaturpflicht,
Reihenfolge und Berechtigungsverhalten.

### Beschlossen

Noch keine Architekturentscheidungen. Die vorgeschlagenen Leitentscheidungen werden im Rahmen von Phase 0 einzeln
bestätigt oder angepasst.

## Referenzen

- International Council on Archives: [ISAD(G), Second Edition](https://www.ica.org/app/uploads/2024/01/CBPS_2000_Guidelines_ISADG_Second-edition_EN.pdf)
- International Council on Archives: [Records in Contexts – Foundations of Archival Description, Version 1.0](https://www.ica.org/app/uploads/2023/12/RiC-FAD-1.0.pdf)
