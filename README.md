# OLDAPlib
Basic library for OLDAP Python-based backend. OLDAP relies as much as possible on
standard ontologies. Currently, the following ontologies are being used:
- xs: `<http://www.w3.org/2001/XMLSchema#>`
- rdf: `<http://www.w3.org/1999/02/22-rdf-syntax-ns#>`
- rdfs: `<http://www.w3.org/2000/01/rdf-schema#>`
- owl: `<http://www.w3.org/2002/07/owl#>`
- skos: `<http://www.w3.org/2004/02/skos/core#>`
- sh: `<http://www.w3.org/ns/shacl#>`

## Setup of IRI's and namespaces

The generic base IRI that is to be used has the form of
```
http://oldap.org/<location>
```
`<location>` is a **unique name** identifying the OLDAP installation of the
type [NCName](https://www.w3.org/TR/1999/REC-xml-names-19990114/#NT-NCName).

### System namespace

#### System ontologies and SHACL files
All system relevant definitions like system-wide ontologies or shacl definitions
are in a graph named
```
http://oldap.org/base#
```

#### System-wide data
Data such as project information, user data etc. is in a graph named
```
http://oldap.org/<location>/data#
```

### Project specific graphs
Each project has several namespaces (aka "named graphs")

#### Project specific data
All project specific data resides in a graph named
```
http://oldap.org/<location>/<project>/data#
```
The project name must be unique to the location and is of
type [NCName](https://www.w3.org/TR/1999/REC-xml-names-19990114/#NT-NCName).

## Media object

- originalName: `<http://purl.org/dc/terms/originalName>`
- originalMimeType: `<http://purl.org/dc/terms/format>`
- mediaserverUri: xsd:anyURI
- project: `<http://oldap.org/base#project>`

