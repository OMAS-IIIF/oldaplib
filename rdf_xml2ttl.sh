#!/bin/bash
poetry run python - <<PY
from rdflib import Graph
g = Graph().parse("$1")
g.serialize("$2", format="turtle")
PY