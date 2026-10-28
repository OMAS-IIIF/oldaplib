"""Inventory transaction syntax in Git-tracked Python, including indirect helpers.

This is a conservative lexical/AST audit, not a complete dynamic call graph.
It records each call/reference with its enclosing function and separates tests,
tools and runtime code. Also scans untracked Python so new code cannot disappear
from the audit. Parse errors are fatal. Writes JSON to stdout; never imports code.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
from pathlib import Path
import subprocess

NAMES = {
    "transaction_start", "transaction_query", "transaction_update", "transaction_commit",
    "transaction_abort", "in_transaction", "resource_transaction", "_resource_transaction",
    "resource_operation", "coordinated_domain_operation", "resource_query",
    "safe_query", "safe_update", "safe_commit", "get_modified_by_iri", "set_modified_by_iri",
    "read_modified_shacl", "read_modtime_shacl", "before_commit", "mutation_gate",
    "update_query", "upload_turtle", "clear_graph", "clear_repo", "move_graph",
}
OWNERS = {"transaction_start", "resource_transaction", "resource_operation", "coordinated_domain_operation"}


def category(path: Path) -> str:
    """Classify evidence without silently excluding fixtures and operational tools."""
    if any(p in {"test", "tests"} for p in path.parts) or path.name.startswith("test_"):
        return "test"
    if path.parts[0] in {"tools", "scripts", "research", "docs", "doc"}:
        return "tool"
    return "runtime-or-script"


class Inventory(ast.NodeVisitor):
    """Track scopes and syntax locations without claiming resolved Python dispatch."""
    def __init__(self):
        self.scope = []
        self.entries = []
        self.functions = []

    def visit_ClassDef(self, node):
        self.scope.append(node.name)
        self.generic_visit(node)
        self.scope.pop()

    def visit_FunctionDef(self, node):
        self.scope.append(node.name)
        function = {"name": ".".join(self.scope), "line": node.lineno, "end": node.end_lineno,
                    "decorators": [ast.unparse(d) for d in node.decorator_list]}
        self.functions.append(function)
        self.generic_visit(node)
        self.scope.pop()

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_Call(self, node):
        name = node.func.attr if isinstance(node.func, ast.Attribute) else (
            node.func.id if isinstance(node.func, ast.Name) else "")
        if name in NAMES:
            self.entries.append({"scope": ".".join(self.scope) or "<module>", "line": node.lineno,
                                 "kind": "call", "name": name, "expression": ast.unparse(node.func)})
        for keyword in node.keywords:
            if keyword.arg == "before_commit":
                self.entries.append({"scope": ".".join(self.scope), "line": node.lineno,
                                     "kind": "callback", "name": "before_commit",
                                     "expression": ast.unparse(keyword.value)})
        self.generic_visit(node)

    def visit_Attribute(self, node):
        # Record method values passed as callbacks as well as direct calls.
        if node.attr in NAMES:
            self.entries.append({"scope": ".".join(self.scope) or "<module>", "line": node.lineno,
                                 "kind": "reference", "name": node.attr, "expression": ast.unparse(node)})
        self.generic_visit(node)


def scan(root: Path) -> dict:
    """Read one Git repository and retain source hashes for reproducibility."""
    paths = subprocess.check_output(["git", "-C", str(root), "ls-files", "-z", "--cached", "--others",
                                     "--exclude-standard", "--", "*.py"]).decode().split("\0")
    files = []
    parsed = 0
    for name in sorted(set(filter(None, paths))):
        path = root / name
        if not path.is_file():
            continue
        source = path.read_text()
        tree = ast.parse(source, filename=str(path))
        parsed += 1
        visitor = Inventory()
        visitor.visit(tree)
        relevant = [f for f in visitor.functions if any(d in OWNERS for d in f["decorators"])]
        if not visitor.entries and not relevant:
            continue
        files.append({"path": name, "category": category(Path(name)),
                      "sha256": hashlib.sha256(source.encode()).hexdigest(),
                      "functions": visitor.functions, "entries": visitor.entries})
    return {"repository": root.name,
            "commit": subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"], text=True).strip(),
            "python_files_parsed": parsed, "files": files}


def main() -> None:
    """Scan each requested repository; report errors rather than an incomplete success."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("repositories", nargs="+", type=Path)
    args = parser.parse_args()
    result = {"schema": 1, "method": "AST call/reference/decorator inventory; dynamic dispatch requires manual review",
              "repositories": [scan(root.resolve()) for root in args.repositories]}
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
