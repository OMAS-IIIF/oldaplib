# Apply only after a zero-row preflight and backup, to an isolated target.
# One update reverses every legacy assertion and removes it atomically.
# RDF set semantics make already-present reverse edges and replay harmless.
PREFIX fasnacht: <http://fasnacht.digital/ns/>
PREFIX dcterms: <http://purl.org/dc/terms/>
WITH fasnacht:data
DELETE { ?parent dcterms:hasPart ?child }
INSERT { ?child dcterms:isPartOf ?parent }
WHERE { ?parent dcterms:hasPart ?child }
