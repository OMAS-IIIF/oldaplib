.PHONY: help docs test build publish coverage

help:
	@echo "Usage: make [target] ..."
	@echo ""
	@echo "Available targets:"
	@echo "  docs     		Build the MkDocs documentation"
	@echo "  help     		Show this help message"
	@echo "  test     		Run all tests"
	@echo "  test-secure     Run all tests with GraphDB in secure mode"
	@echo "  build    		Build the distribution package"
	@echo "  publish  		Publish the package to PiPy"
	@echo "  coverage 		Get the coverage rate of the unittests"

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

