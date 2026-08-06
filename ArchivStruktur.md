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

Alle Knoten der archivischen Hierarchie werden durch eine gemeinsame ResourceClass dargestellt,
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

Diese Werte sind feste Named Individuals der Shared-Ontologie. Das SHACL-Modell begrenzt `archiveLevel` mit `sh:in`
auf genau diese Werte. Neue Archivstufen werden deshalb nicht durch Listenadministration oder einzelne Projekte,
sondern nur als bewusste, versionierte Erweiterung der Shared-Ontologie eingeführt.

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

Fachliche Objekte, Ereignisse oder andere Projektdomänen-Ressourcen werden ebenfalls nicht mit der Archiveinheit
gleichgesetzt. Eine Archiveinheit kann über das optionale, mehrwertige `schema:about` auf beliebige bestehende
`oldap:Thing`-Ressourcen verweisen. Das Shared-Modell kennt deshalb keine projektspezifischen Zielklassen und führt
keine zusätzliche Markerklasse wie `shared:ArchiveSubject` ein. Projektoberflächen dürfen die auswählbaren Zielklassen
für ihren Anwendungsfall einschränken, ohne die generische Ontologie zu verengen.

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
- Eine optionale Position bezeichnet die Reihenfolge unter direkten Geschwistern.

Folgende Regeln werden vorerst bewusst **nicht** im SHACL-Grundmodell erzwungen:

- Mindestanzahl von Kindern
- eine feste Abfolge der Archivstufen
- XOR-Regeln für unterschiedliche Arten von Untereinheiten
- das Verbot, einzelne Ebenen zu überspringen

Leere Einheiten müssen während der inkrementellen Erfassung zulässig sein. Strengere fachliche Regeln können später
als konfigurierbares Archivprofil, Anwendungsvalidierung oder Warnung in der Benutzeroberfläche ergänzt werden.

## Implementiertes minimales Modell

Das Ontologie-MVP ist seit Version `0.2.0` direkt in `oldaplib/ontologies/shared.trig` enthalten; Phase 3A erweitert
es in Version `0.3.0` und Phase 3B in Version `0.4.0` ausschliesslich um optionale Erschliessungsfelder. Version `0.5.0`
ergänzt den generischen inhaltlichen Bezug. Die Datei bleibt die massgebliche Quelle für die Shared-Ontologie; das
Projekt-YAML-Format von `oldap-tools` wird weiterhin nur für Projektontologien verwendet.

| Element | Kardinalität im MVP | Zweck |
|---|---:|---|
| `shared:ArchiveUnit` | – | Gemeinsame ResourceClass aller archivischen Beschreibungseinheiten |
| `schema:name` | 1..n Sprachwerte | Verpflichtender mehrsprachiger Titel mit höchstens einem Wert pro Sprache |
| `shared:archiveLevel` | genau 1 | Kontrollierte Archivstufe |
| `shared:parentArchiveUnit` | 0..1 | Direkte hierarchische Elternbeziehung |
| `schema:identifier` | 0..1 | Optionale, zunächst manuell vergebene Archivsignatur |
| `schema:description` | 0..n Sprachwerte | Optionaler Inhalt und Zusammenfassung, höchstens ein Wert pro Sprache |
| `dcterms:temporal` | 0..1 | Optionale Laufzeit als bestehender `oldap:Dating`-Wert |
| `schema:materialExtent` | 0..n Sprachwerte | Optionaler Umfang und Medium, höchstens ein Wert pro Sprache |
| `dcterms:creator` | 0..n | Optionale Verknüpfungen zu Bestandsbildnern vom Typ `dcterms:Agent` |
| `dcterms:provenance` | 0..n Sprachwerte | Optionale Überlieferungs- und Besitzgeschichte, höchstens ein Wert pro Sprache |
| `schema:conditionsOfAccess` | 0..n Sprachwerte | Optionale informative Zugangsbedingungen, höchstens ein Wert pro Sprache |
| `schema:about` | 0..n | Optionale inhaltliche Bezüge zu beliebigen `oldap:Thing`-Ressourcen |
| `schema:position` | 0..1 | Optionale ganzzahlige Reihenfolge unter Geschwistern |
| `shared:hasMediaObject` | 0..n | Verknüpfung zu digitalen Repräsentationen |

SHACL definiert Kardinalitäten, Datentypen, Werteklassen und die erlaubten Archivstufen. OWL deklariert die Klassen,
Named Individuals und Properties; Einschränkungen der wiederverwendeten Standard-Properties auf `ArchiveUnit` bleiben
bewusst in SHACL, damit ihre globale Bedeutung nicht verfälscht wird. Ein fokussierter Strukturtest stellt sicher,
dass beide Hälften synchron bleiben.

In Phase 1 wurden bewusst keine spezialisierten Python-Klassen eingeführt. Die generischen
`ResourceInstance`-Funktionen bleiben für Erstellen, Lesen, normale Metadatenänderungen, Löschen und Suchen zuständig.
Phase 2 ergänzt nur für das Verschieben eine kleine `ArchiveTree`-Servicegrenze, weil die Zyklusprüfung nicht sicher
der Benutzeroberfläche überlassen werden darf.

## Inkrementelle Entwicklungsstrategie

Jede Phase soll einen eigenständig nutzbaren vertikalen Schnitt liefern. Der nächste Schritt beginnt erst, wenn der
vorherige mit realistischen Daten erprobt wurde.

### Phase 0: Interne Modellentscheidung – abgeschlossen

- Die notwendige archivfachliche Kompetenz ist im OLDAP-Team vorhanden; eine vorgängige Validierung durch das
  Fasnachtsprojekt ist deshalb keine Voraussetzung.
- Das generische Knotenmodell, die festen Archivstufen und die minimalen Metadaten wurden intern festgelegt.
- Ein kleiner technischer Testbaum kann bei den CRUD- und Abfragetests entstehen, statt als separates Fachprojekt
  vorbereitet zu werden.

**Ergebnis:** Der MVP-Umfang ist entschieden und die Ontologieimplementierung kann unmittelbar erfolgen.

### Phase 1: Ontologie-MVP – abgeschlossen

- [x] `ArchiveUnit`, Elternbeziehung, Archivstufe und minimale Metadaten in der Shared-Ontologie definieren.
- [x] Kontrollierte Archivstufen als benannte RDF-Individuen anlegen.
- [x] Einen GraphDB-unabhängigen Strukturtest für SHACL und OWL ergänzen.
- [x] Einen kleinen technischen Beispielbaum und Integrationstests ergänzen.
- [x] Generische CRUD- und Suchoperationen mit dem Referenzbaum prüfen.
- Noch keine besondere Archiv-API und keine konfigurierbaren Hierarchieregeln einführen.

Der Integrationstest `TestObjectFactory.test_archive_unit_reference_tree_crud_and_search` erzeugt diesen technischen
Referenzbaum zur Laufzeit:

```text
REF                  [Fonds]
└── REF-01           [Series]
    └── REF-01-01    [File]
        ├── ...-001  [Item, Position 1]
        └── ...-002  [Item, Position 2]
```

Der Test prüft das Erstellen aller Knoten, das Lesen von Wurzel und Kind, das Aktualisieren einer Beschreibung, die
Suche nach direkten Kindern mit Filter auf Elternknoten und Archivstufe, die Sortierung nach `schema:position` sowie
das Löschen. Der Baum wird anschliessend vollständig entfernt. Der Testaufbau lädt die aktuelle `shared.trig`
explizit, damit nicht unbemerkt eine ältere, bereits in GraphDB vorhandene Shared-Ontologie getestet wird.

**Ergebnis:** Archivbäume können mit bestehenden generischen OLDAP-Mitteln gespeichert, gelesen, geändert, gesucht
und gelöscht werden. Eine besondere Archiv-API ist für diesen Grundumfang nicht erforderlich.

### Phase 2: Minimale Baumoperationen – abgeschlossen

- [x] Direkte Kinder mit der bestehenden strukturierten OLDAP-Suche laden.
- [x] Den Pfad zur Wurzel aus den geladenen Vorfahren darstellen.
- [x] Teilbäume in der Oberfläche schrittweise und nur beim Aufklappen laden.
- [x] Archiveinheiten über eine kleine Backend-Servicegrenze verschieben und Zyklen verhindern.
- [x] Die optionale `schema:position` beim Verschieben setzen oder entfernen und Geschwister danach sortieren.
- [x] Leere Archiveinheiten in der Oberfläche löschbar machen und nichtleere Einheiten durch Vorprüfungen sowie die
  vorhandene generische Referenzprüfung schützen.

Die Aufgabenteilung bleibt bewusst klein:

- `oldaplib/src/archive_tree.py` enthält nur `path_to_root()` und das integritätskritische `move()`.
- `POST /data/{project}/{instiri}/archive-move` ist die HTTP-Grenze. Der normale Instanz-Update-Endpunkt lehnt
  Änderungen an `shared:parentArchiveUnit` und `schema:position` für Archiveinheiten ab, damit die Zyklusprüfung nicht
  umgangen werden kann.
- `src/lib/components/admin/archive/ArchiveTree.svelte` in FasnachtsPage kapselt Darstellung, Lazy Loading,
  Pfadanzeige und den einfachen Verschiebe-Dialog. Die vorhandene grosse Archivseite bindet diese Komponente nur ein.
- Direkte Kinder und Wurzeln werden weiterhin über die generische Suche abgefragt; es gibt keinen eigenen Lese-Endpunkt
  und keinen vorab geladenen Gesamtbaum.

Beim Verschieben werden ausschliesslich Elternreferenz und optional die Geschwisterposition geändert. Signatur,
Berechtigungen und publizierte Links bleiben unverändert. Berechtigungen bleiben pro Archiveinheit unabhängig.
Archiveinheiten mit Kindern können bereits heute nicht gelöscht werden, weil die generische `ResourceInstance.delete()`-
Prüfung eingehende Referenzen erkennt. Die Oberfläche erlaubt das Löschen deshalb nur nach einer Bestätigung und prüft
zuvor, dass die Einheit keine Kinder und keine mit `shared:hasMediaObject` verknüpften Medien besitzt. Titel,
Archivstufe und weitere beschreibende Metadaten verhindern das Löschen eines ansonsten leeren Blatts nicht. Weitere
eingehende Referenzen werden weiterhin vom Backend abgewiesen. Eine kaskadierende Löschung wird nicht eingeführt.

**Ergebnis:** Die Struktur kann schrittweise navigiert, nach Position sortiert und über eine kleine, zyklusgeprüfte
Servicegrenze verschoben werden, ohne ein zusätzliches Archiv-Subsystem aufzubauen.

### Phase 3: Archivische Erschliessungsmetadaten – abgeschlossen

#### Phase 3A: Minimaler Erschliessungssatz – abgeschlossen

- [x] Die bestehende `schema:description` fachlich als **Inhalt und Zusammenfassung** bezeichnen.
- [x] `dcterms:temporal` mit genau höchstens einem bestehenden `oldap:Dating`-Wert als **Laufzeit** ergänzen.
- [x] `schema:materialExtent` als mehrsprachiges Feld für **Umfang und Medium** ergänzen.
- [x] `dcterms:creator` als mehrwertige Verknüpfung zu `dcterms:Agent` für **Bestandsbildner** ergänzen.
- [x] Alle neuen Angaben optional halten; verpflichtend bleiben nur Titel und Archivstufe.
- [x] Erstellen und Bearbeiten in einer kleinen `ArchiveUnitEditor.svelte`-Komponente über die generische OLDAP-API
  ermöglichen. Elternknoten und Position bleiben ausserhalb dieses Metadateneditors und benutzen weiterhin die
  gesicherte Baumoperation aus Phase 2.
- [x] SHACL, OWL, GraphDB-Rundlauf, Frontend-Payloads und API-Grenze testen.

Die Erweiterung ist additiv und rückwärtskompatibel: Bestehende Archiveinheiten bleiben gültig, weil kein neues
Pflichtfeld eingeführt und keine vorhandene Property entfernt oder umgedeutet wurde. Es ist deshalb weder eine
Datenmigration noch ein Schnitt erforderlich. Bestehende Fasnachts-Archivdaten werden in dieser Phase nicht verändert.
Sie gelten weiterhin als Testdaten und können nach Abschluss der Architekturarbeiten mit einem separat geprüften,
eng auf Archivklassen begrenzten Bereinigungsschritt entfernt und neu erfasst werden. Geschichten und andere
Nicht-Archivressourcen dürfen von diesem späteren Schritt ausdrücklich nicht berührt werden.

**Ergebnis 3A:** Archiveinheiten können mit Titel, Stufe, Signatur, Inhalt, Laufzeit, Umfang/Medium und einem oder
mehreren Bestandsbildnern erfasst werden. Gemeinsame Angaben können auf der höchsten passenden Einheit stehen und
müssen nicht in Kindern dupliziert werden.

#### Phase 3B: Überlieferungsgeschichte und Zugangsbedingungen – abgeschlossen

- [x] `dcterms:provenance` als optionalen mehrsprachigen Text für die **Überlieferungs- und Besitzgeschichte** ergänzen.
- [x] `schema:conditionsOfAccess` als optionalen mehrsprachigen Informationstext für **Zugangsbedingungen** ergänzen.
- [x] Zugangsbedingungen fachlich und in der Oberfläche klar von technischen OLDAP-Rollen und Berechtigungen trennen.
- [x] Erstellen, Lesen, Ändern und gezieltes Entfernen beider optionalen Angaben über den bestehenden
  `ArchiveUnitEditor.svelte` ermöglichen.
- [x] SHACL, OWL, externe Property-Registrierung und Frontend-Payloads mit fokussierten Tests abdecken.

Beide Properties sind optionale `rdf:langString`-Werte mit höchstens einem Text pro Sprache. Ein eingetragener
Zugangshinweis dokumentiert beispielsweise eine Voranmeldung oder Sperrfrist, erzwingt diese aber nicht technisch.
Wirksame Zugriffsbeschränkungen müssen weiterhin separat über OLDAP-Rollen und DataPermissions eingerichtet werden.
Benutzungs- und Reproduktionsbedingungen, innere Ordnung sowie physische Standorte bleiben bewusst ausserhalb dieser
Teilphase. Konkrete Medienlizenzen verbleiben bei den Medienobjekten.

Die Erweiterung ist erneut additiv und rückwärtskompatibel. Bestehende Archiveinheiten bleiben ohne die beiden neuen
Felder gültig; eine Datenmigration ist nicht erforderlich.

**Ergebnis Phase 3:** Die Struktur unterstützt nach den schrittweise bestätigten Teilphasen eine praktisch
ausreichende archivische Erschliessung.

### Manueller YAML-Strukturimport – abgeschlossen

Der manuelle YAML-Import ist der generische Normalfall für den Aufbau grösserer Archivstrukturen. Das Format ist
rekursiv und projektneutral. Es kennt keine Vereine oder andere Fasnachtsspezifika und erlaubt mehrere Wurzeln. So kann
beispielsweise jeder Verein im Projekt Fasnacht einen eigenen `Fonds` erhalten, ohne das Shared-Modell oder das
Dateiformat um einen Vereinsbegriff zu erweitern.

Jede YAML-Einheit besitzt einen dokumentweit eindeutigen, NCName-kompatiblen `id`. Dieser wird deterministisch zur
Projekt-IRI, beispielsweise `bmg` im Projekt `fasnacht` zu `fasnacht:bmg`. Verpflichtend sind ausserdem Archivstufe und
Titel; alle bereits in `shared:ArchiveUnit` vorhandenen Erschliessungsfelder können optional mitgegeben werden. Ein
Skalartext verwendet die Standardsprache des Dokuments, mehrsprachige Texte werden als Sprach-Mapping geschrieben.

`oldap-tools` stellt dafür drei klar getrennte Schritte bereit:

```text
archive validate  →  lokale Schema- und Inhaltsprüfung
archive load      →  OLDAP-Preflight ohne Änderungen (Standard)
archive load --apply → ausschliesslich neue Archiveinheiten erzeugen
```

Der Import ist **create-only**. Bestehende Ziel-IRIs führen zu einem Fehler; es gibt kein Zusammenführen nach Titel oder
Signatur und kein Aktualisieren, Verschieben oder Löschen vorhandener Einheiten. Eine neue Teilstruktur kann trotzdem
additiv unter eine bestehende Archiveinheit gehängt werden: Nur eine oberste YAML-Einheit darf mit `parent` auf deren
vorhandene IRI zeigen. Der Preflight prüft Zielkollisionen sowie Existenz und Klasse solcher Elternknoten. Eltern werden
vor Kindern erzeugt; bei einem Fehler versucht das Werkzeug, alle im laufenden Import bereits erzeugten Einheiten in
umgekehrter Reihenfolge wieder zu entfernen.

Die massgeblichen Dateien liegen in `oldap-tools`:

- `src/oldap_tools/schemas/archive_schema.yaml`: maschinenlesbares Yamale-Schema
- `docs/archive-yaml.md`: vollständige Format- und Betriebsdokumentation
- `examples/archive-structure.yaml`: kleines Beispiel mit zwei unabhängigen Beständen
- `src/oldap_tools/archive.py`: Validierung, Preflight und create-only Import

Ein späterer Generator aus der Staging-Struktur soll genau dasselbe YAML erzeugen. Damit bleiben manuelle Definition und
automatisch vorbereiteter Entwurf zwei Eingänge in denselben validierten Importweg. Der Generator, technische
Ordnerregeln und die Medienübernahme sind nicht Bestandteil dieses ersten Schritts.

### Phase 4: Vermittlung und Kontextualisierung

- [x] Mit optionalem `schema:about` eine generische Shared-Grundlage für inhaltliche Bezüge schaffen.
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

### Nach Phase 3 und später

Die Erschliessungsangaben aus Phase 3 bleiben optional; verpflichtend sind weiterhin nur Titel und Archivstufe.
Bestandsbildner werden als bestehende `dcterms:Agent`-Ressourcen verknüpft, und eine Einheit kann mehrere
Bestandsbildner besitzen. Zugangsbedingungen sind reine Informationstexte und keine technischen Berechtigungen. Der
Dokumentbegriff ist im Grundmodell geklärt: `shared:Item` bezeichnet die kleinste archivisch beschriebene Einheit und
ersetzt keine projektspezifische Objekt- oder Ereignisressource. Die fachliche Abgrenzung mehrteiliger Unterlagen bleibt
eine Erfassungsentscheidung und wird nicht durch eine zusätzliche Grundmodellregel erzwungen.

1. **Physische Ordnung:** Muss die physische Lagerstruktur unabhängig von der intellektuellen Archivordnung modelliert
    werden?
2. **Vererbung in der Anzeige:** Welche Metadaten einer übergeordneten Einheit sollen Kinder in der Oberfläche
    kontextuell anzeigen, ohne diese Daten zu duplizieren?
3. **Staging-Publikation:** Erzeugt der Publikationsprozess neue Archiveinheiten, ordnet er Medien bestehenden Einheiten
    zu oder muss er beide Varianten unterstützen?
4. **Standardaustausch:** Welche konkreten Austauschformate oder Zielsysteme haben Priorität? Ohne benannten
    Austauschpartner soll kein komplexes Mapping implementiert werden.

## Entscheidungsstand

### Beschlossen

- Die universelle Archivdefinition liegt als Teil von `shared.trig` in der Shared-Ontologie. Es gibt keine separate
  Archiv-TriG-Datei und kein zusätzliches Shared-YAML als zweite Quelle.
- Eine generische `shared:ArchiveUnit` bildet alle Hierarchieebenen ab; auch eine Bestandsgruppe ist eine vollwertige
  Archiveinheit.
- Die Archivstufe wird als kontrollierte Eigenschaft und nicht durch Unterklassen modelliert.
- `ArchiveLevel` ist eine OWL-Klasse mit sieben festen Named Individuals. Es ist keine veränderbare OLDAP-Taxonomie.
- Die Hierarchie verwendet eine einfache Elternreferenz mit höchstens einem Elternknoten. Mehrere Wurzeleinheiten und
  damit mehrere unabhängige Archivbäume pro Projekt sind im MVP erlaubt; eine zusätzliche `Archive`-Klasse gibt es nicht.
- `schema:name` ist der verpflichtende mehrsprachige Titel. `schema:identifier`, `schema:description` und
  `schema:position` werden als bestehende Standard-Properties wiederverwendet.
- Phase 3A verwendet zusätzlich `dcterms:temporal` für höchstens eine `oldap:Dating`-Laufzeit,
  `schema:materialExtent` für mehrsprachigen Umfang und Medium sowie das mehrwertige `dcterms:creator` für
  Bestandsbildner vom Typ `dcterms:Agent`. Alle drei Angaben bleiben optional.
- Phase 3B verwendet optionales mehrsprachiges `dcterms:provenance` für die Überlieferungs- und Besitzgeschichte sowie
  optionales mehrsprachiges `schema:conditionsOfAccess` für informative Zugangsbedingungen. Letztere verändern oder
  ersetzen keine technischen OLDAP-Berechtigungen.
- `schema:about` verknüpft eine Archiveinheit optional und mehrwertig mit inhaltlich bezogenen Ressourcen. Die lokale
  SHACL-Zielklasse ist `oldap:Thing`; es gibt weder eine Shared-Markerklasse noch einen globalen OWL-Range für die
  externe schema.org-Property. Projektspezifische Klassen und Auswahlregeln bleiben ausserhalb der Shared-Ontologie.
- `shared:Item` ist die kleinste archivisch beschriebene Einheit. Fachliche Objekte oder Ereignisse bleiben davon
  getrennte Ressourcen und können über `schema:about` verbunden werden.
- Der Metadateneditor verändert weder `shared:parentArchiveUnit` noch `schema:position`; Strukturänderungen bleiben an
  die zyklusgesicherte Baumoperation aus Phase 2 gebunden.
- Die Phase-3A-Erweiterung ist additiv und benötigt keine Migration bestehender Daten. Eine spätere Bereinigung der als
  Testdaten betrachteten Fasnachts-Archivressourcen muss selektiv erfolgen und Geschichten sowie andere Projektdaten
  bewahren.
- Die Signatur ist im MVP optional und wird nicht automatisch aus der Hierarchie erzeugt.
- Die optionale ganzzahlige `schema:position` kann eine manuelle Geschwisterreihenfolge ausdrücken; Eindeutigkeit und
  automatische Neunummerierung werden im Grundmodell nicht erzwungen.
- Archiveinheiten und Medienobjekte sind getrennte Konzepte und werden mit `shared:hasMediaObject` explizit verknüpft.
  Das Shared-Grundmodell begrenzt nicht, von wie vielen Archiveinheiten dasselbe Medienobjekt referenziert werden darf.
- Staging und dauerhafte Archivordnung bleiben getrennte Subsysteme.
- Der manuelle Archivstrukturimport verwendet ein projektneutrales, rekursives YAML mit mehreren möglichen Wurzeln.
  Stabile YAML-IDs werden zu Projekt-IRIs. Der erste Importmodus ist create-only, standardmässig ein Dry-run und kann
  neue Teilbäume über eine explizite vorhandene Eltern-IRI additiv ergänzen; bestehende Ressourcen werden nie implizit
  zusammengeführt, aktualisiert, verschoben oder gelöscht.
- Ein späterer Staging-Baum-Generator erzeugt dasselbe Archiv-YAML und führt keinen zweiten Importpfad ein.
- Das Grundmodell erzwingt keine starre Abfolge, Mindestanzahl von Kindern oder projektspezifische Hierarchieprofile.
- Baumansichten laden Wurzeln und direkte Kinder schrittweise über die generische Suche; ein eigener Archiv-Lese-Endpunkt
  und das Laden des vollständigen Baums sind vorerst nicht nötig.
- Strukturänderungen laufen über eine kleine `ArchiveTree`-Servicegrenze. Sie verhindert Selbstreferenzen und das
  Verschieben unter einen Nachfahren; der generische HTTP-Update-Endpunkt darf diese Grenze nicht umgehen.
- Verschieben ändert nur `shared:parentArchiveUnit` und optional `schema:position`. Signaturen, Berechtigungen und
  publizierte Links bleiben unverändert; Berechtigungen bleiben pro Archiveinheit unabhängig.
- Leere Archiveinheiten dürfen nach Bestätigung gelöscht werden. Kinder, verknüpfte Medien oder andere eingehende
  Referenzen verhindern das Löschen; es gibt keine kaskadierende Löschung im MVP.
- Erweiterte Regeln, Standards und Services werden inkrementell anhand konkreter Anwendungsfälle eingeführt.

### Noch nicht entschieden

Die nummerierten Punkte im Abschnitt [Offene Fragen](#offene-fragen).

## Referenzen

- International Council on Archives: [ISAD(G), Second Edition](https://www.ica.org/app/uploads/2024/01/CBPS_2000_Guidelines_ISADG_Second-edition_EN.pdf)
- International Council on Archives: [Records in Contexts – Foundations of Archival Description, Version 1.0](https://www.ica.org/app/uploads/2023/12/RiC-FAD-1.0.pdf)
