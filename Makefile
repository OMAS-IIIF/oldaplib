.PHONY: help docs test bump-patch-level bump-minor-level bump-major-level build publish coverage getontos loadontos

help:
	@echo "Usage: make [target] ..."
	@echo ""
	@echo "Available targets:"
	@echo "  docs     		  Build the MkDocs documentation"
	@echo "  help     		  Show this help message"
	@echo "  test     		  Run all tests"
	@echo "  test-secure      Run all tests with GraphDB in secure mode"
	@echo "  bump-patch-level Increment patch level of version number"
	@echo "  bump-minor-level Increment minor level of version number"
	@echo "  bump-major-level Increment major level of version number"
	@echo "  build    		  Build the distribution package"
	@echo "  publish  		  Publish the package to PiPy"
	@echo "  coverage 		  Get the coverage rate of the unittests"
	@echo "  getontos         Download standard ontologies 'dcterm', 'skos' & 'schema'"
	@echo "  loadontos        Load standard ontologies into GraphDB"

docs:
	poetry run mkdocs serve

test:
	OLDAP_TS_SERVER=http://localhost:7200 \
	OLDAP_TS_REPO=oldap \
	OLDAP_REDIS_URL=redis://localhost:6379 \
	poetry run python3 -m unittest -v

test-secure:
	OLDAP_TS_SERVER=http://localhost:7200 \
	OLDAP_TS_REPO=oldap \
	OLDAP_TS_USER=oldap \
	OLDAP_TS_PASSWORD=MyOldap \
	OLDAP_REDIS_URL=redis://localhost:6379 \
	poetry run python3 -m unittest -v

bump-patch-level:
	poetry run bump2version patch
	git push

bump-minor-level:
	poetry run bump2version minor
	git push

bump-major-level:
	poetry run bump2version major
	git push

build:
	poetry build

publish:
	poetry publish

coverage:
	OLDAP_TS_SERVER=http://localhost:7200 \
	OLDAP_TS_REPO=oldap \
	OLDAP_REDIS_URL=redis://localhost:6379 \
	poetry run coverage run -m unittest -v
	poetry run coverage html

getontos:
	curl -L -o oldaplib/ontologies/standard/dcterms.ttl https://www.dublincore.org/specifications/dublin-core/dcmi-terms/dublin_core_terms.ttl
	curl -L -o oldaplib/ontologies/standard/skos.xml http://www.w3.org/2004/02/skos/core
	curl -L -o oldaplib/ontologies/standard/schemaorg.ttl https://schema.org/version/latest/schemaorg-current-https.ttl
	./rdf_xml2ttl.sh oldaplib/ontologies/standard/skos.xml oldaplib/ontologies/standard/skos.ttl

loadontos:
	curl -X POST \
	  -H 'Content-Type: application/x-trig' \
	  --data-binary @oldaplib/ontologies/oldap.trig \
	  'http://localhost:7200/repositories/oldap/statements'
	curl -X POST \
	  -H 'Content-Type: application/x-trig' \
	  --data-binary @oldaplib/ontologies/admin.trig \
	  'http://localhost:7200/repositories/oldap/statements'
	curl -X POST \
	  -H 'Content-Type: application/x-trig' \
	  --data-binary @oldaplib/ontologies/shared.trig \
	  'http://localhost:7200/repositories/oldap/statements'
	# SKOS
	curl -X POST \
	  -H 'Content-Type: text/turtle' \
	  --data-binary @oldaplib/ontologies/standard/skos.ttl \
	  'http://localhost:7200/repositories/oldap/statements?context=%3Curn:oldap:vocab:skos%3E'
	# DCTERMS
	curl -X POST \
	  -H 'Content-Type: text/turtle' \
	  --data-binary @oldaplib/ontologies/standard/dcterms.ttl \
	  'http://localhost:7200/repositories/oldap/statements?context=%3Curn:oldap:vocab:dcterms%3E'
	curl -X POST \
	  -H 'Content-Type: text/turtle' \
	  --data-binary @oldaplib/ontologies/standard/schemaorg.ttl \
	  'http://localhost:7200/repositories/oldap/statements?context=%3Curn:oldap:vocab:schema%3E'

