.PHONY: help docs test bump-patch-level bump-minor-level bump-major-level build publish coverage

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

