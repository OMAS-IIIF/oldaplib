"""Inventory legacy RDF* string builders for manual migration review.

This lexical AST inventory includes SQL-like string fragments in f-strings, but
not comments. It does not infer call graphs or prove runtime dialect coverage.
RDF 1.2 triple terms (<<(... )>>) are excluded. Only locations are emitted.
"""
import ast
import json
from pathlib import Path
import re


def inventory(root: Path) -> list[dict]:
    """Return enclosing scope and line for each legacy annotation string site."""
    sites = []
    for path in sorted((root / 'oldaplib' / 'src').rglob('*.py')):
        class Visitor(ast.NodeVisitor):
            scope = []

            def visit_ClassDef(self, node):
                self.scope.append(node.name)
                self.generic_visit(node)
                self.scope.pop()

            visit_FunctionDef = visit_ClassDef
            visit_AsyncFunctionDef = visit_ClassDef

            def visit_Constant(self, node):
                if isinstance(node.value, str) and re.search(r'<<(?!\s*\()', node.value):
                    sites.append({'file': str(path.relative_to(root)), 'scope': '.'.join(self.scope),
                                  'line': node.lineno})

        Visitor().visit(ast.parse(path.read_text()))
    return sites


if __name__ == '__main__':
    print(json.dumps({'kind': 'legacy-rdfstar-string-candidates',
                      'sites': inventory(Path(__file__).resolve().parents[2])}, indent=2))
