from enum import unique, Enum


@unique
class SparqlResultFormat(Enum):
    """
    Enumeration of formats that may be returned by the triple store (if the specific store supports these)
    """
    XML ="application/sparql-results+xml"
    JSON = "application/x-sparqlstar-results+json, application/sparql-results+json;q=0.9, */*;q=0.8" # Accept: application/x-sparqlstar-results+json, application/sparql-results+json;q=0.9, */*;q=0.8
    TURTLE = "text/turtle"
    N3 = "text/rdf+n3"
    NQUADS = "text/x-nquads"
    JSONLD = "application/ld+json"
    TRIX = "application/trix"
    TRIG = "application/x-trig"
    TEXT = "text/plain"
