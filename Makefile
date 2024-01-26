.PHONY: help docs test build publish

help:
	@echo "Usage: make [target] ..."
	@echo ""
	@echo "Available targets:"
	@echo "  docs    Build the MkDocs documentation"
	@echo "  help    Show this help message"
	@echo "  test    Run all tests"
	@echo "  build   Build the distribution package"
	@echo "  publish Publish the package to PiPy"

docs:
	poetry run mkdocs serve

test:
	poetry run python3 -m unittest -v

build:
	poetry build

publish:
	poetry publish
