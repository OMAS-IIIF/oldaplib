"""Run synthetic RDF 1.2 and transaction probes against an owned Fuseki process.

Requires a verified Fuseki 6.2.0 distribution and Java 21+. Creates a fresh
persistent dataset under --output, binds loopback only, and terminates its own
server on completion/failure. Never connects to OLDAP/Redis or an existing server.
Writes results.json and process logs; artifacts are retained for inspection.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request

PREFIX = """PREFIX ex: <urn:jena-probe:>
PREFIX oldap: <http://oldap.org/base#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
"""


def main() -> None:
    """Own an isolated Java/Fuseki lifecycle and fail on any violated assertion."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fuseki-home", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True, help="New, nonexistent run directory")
    parser.add_argument("--java", default="java")
    parser.add_argument("--port", type=int, default=3031)
    args = parser.parse_args()
    if args.port not in range(3031, 3040):
        parser.error("Probe ports are restricted to 3031..3039.")
    jar = args.fuseki_home.resolve() / "fuseki-server.jar"
    if not jar.is_file():
        parser.error("Missing fuseki-server.jar")
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    with socket.socket() as guard:
        # Permit a previous probe's TIME_WAIT sockets, never an active listener.
        guard.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        guard.bind(("127.0.0.1", args.port))
    results = {
        "java": subprocess.check_output([args.java, "-version"], stderr=subprocess.STDOUT, text=True).strip(),
        "jar_sha512": hashlib.sha512(jar.read_bytes()).hexdigest(),
        "port": args.port,
        "checks": [],
    }
    process = None
    log = None
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    base = f"http://127.0.0.1:{args.port}/probe"

    def request(path: str, data: bytes | None = None, content_type: str | None = None,
                accept: str = "application/sparql-results+json") -> tuple[int, bytes]:
        """Send only to this runner's still-running child; disable environment proxies."""
        if process is None or process.poll() is not None:
            raise RuntimeError("Owned Fuseki process is not running")
        headers = {"Accept": accept}
        if content_type:
            headers["Content-Type"] = content_type
        req = urllib.request.Request(base + path, data=data, headers=headers)
        try:
            with opener.open(req, timeout=15) as response:
                return response.status, response.read()
        except urllib.error.HTTPError as error:
            return error.code, error.read()

    def update(body: str) -> None:
        status, response = request("/update", (PREFIX + body).encode(), "application/sparql-update")
        assert 200 <= status < 300, (status, response.decode()[:500])

    def query(body: str) -> dict:
        status, response = request("/query", urllib.parse.urlencode({"query": PREFIX + body}).encode(),
                                   "application/x-www-form-urlencoded")
        assert status == 200, (status, response.decode()[:500])
        return json.loads(response)

    def check(name: str, condition: bool = True) -> None:
        assert condition, name
        results["checks"].append(name)
        print("PASS", name, flush=True)

    def start() -> None:
        nonlocal process, log
        log = (output / "fuseki.log").open("a")
        env = os.environ.copy()
        env["FUSEKI_BASE"] = str(output / "server")
        process = subprocess.Popen(
            [args.java, "-Xmx512m", "-jar", str(jar), "--localhost", f"--port={args.port}",
             "--tdb2", f"--loc={output / 'http-dataset'}", "--update", "/probe"],
            cwd=output, env=env, stdout=log, stderr=subprocess.STDOUT,
        )
        for _ in range(100):
            if process.poll() is not None:
                raise RuntimeError("Fuseki exited; inspect fuseki.log")
            try:
                if query("ASK { ?s ?p ?o }").get("boolean") is not None:
                    return
            except (OSError, AssertionError):
                time.sleep(.1)
        raise RuntimeError("Fuseki readiness timeout")

    def stop() -> None:
        nonlocal process, log
        if process is not None:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=20)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)
            process = None
        if log is not None:
            log.close()
            log = None

    try:
        java_probe = Path(__file__).with_name("JenaTransactionProbe.java").resolve()
        local = subprocess.run(
            [args.java, "-Xmx512m", "--class-path", str(jar), str(java_probe), str(output / "java-dataset")],
            text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=60,
        )
        (output / "java-transactions.log").write_text(local.stdout)
        assert local.returncode == 0, local.stdout
        results["java_transaction_checks"] = [line for line in local.stdout.splitlines() if line.startswith("PASS ")]
        check("Java transaction probe", len(results["java_transaction_checks"]) == 4)
        # This separate Java process demonstrates a readable bounded command,
        # not a replacement for existing Python transaction callbacks.
        composition = subprocess.run(
            [args.java, "-Xmx512m", "--class-path", str(jar),
             str(Path(__file__).with_name("JenaCompositionProbe.java").resolve()),
             str(output / "composition-dataset")],
            text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=60,
        )
        (output / "composition.log").write_text(composition.stdout)
        assert composition.returncode == 0, composition.stdout
        results["composition_checks"] = [line for line in composition.stdout.splitlines() if line.startswith("PASS ")]
        check("Bounded HTTP composition probe", len(results["composition_checks"]) == 13)
        (output / "http-dataset").mkdir()
        start()
        check("Pinned server version", "Apache Jena Fuseki 6.2.0" in (output / "fuseki.log").read_text())

        # Base relation is explicitly asserted; the annotation has a stable identity.
        grants = """GRAPH ex:data {
          ex:item oldap:attachedToRole ex:readerRole .
          ex:grant rdf:reifies <<( ex:item oldap:attachedToRole ex:readerRole )>> ;
                   oldap:hasDataPermission oldap:DATA_VIEW .
        } GRAPH ex:admin {
          ex:alice oldap:hasRole ex:readerRole ; oldap:inProject ex:project .
          ex:adminGrant rdf:reifies <<( ex:alice oldap:inProject ex:project )>> ;
                        oldap:hasAdminPermission oldap:ADMIN_CREATE .
        }"""
        update("INSERT DATA { " + grants + " }")
        permission = """ASK { GRAPH ex:admin { ex:alice oldap:hasRole ?role }
          GRAPH ex:data { ex:item oldap:attachedToRole ?role .
          ?grant rdf:reifies <<( ex:item oldap:attachedToRole ?role )>> ;
                 oldap:hasDataPermission oldap:DATA_VIEW } }"""
        check("Explicit reifier permission join", query(permission)["boolean"])
        check("Admin permission annotation", query("""ASK { GRAPH ex:admin {
          ?grant rdf:reifies <<( ex:alice oldap:inProject ex:project )>> ;
                 oldap:hasAdminPermission oldap:ADMIN_CREATE } }""")["boolean"])
        check("Membership does not invent a default permission", not query("""ASK { GRAPH ex:admin {
          ?grant rdf:reifies <<( ex:alice oldap:hasRole ex:readerRole )>> ;
                 oldap:hasDefaultDataPermission ?permission } }""")["boolean"])
        update("""INSERT DATA { GRAPH ex:admin {
          ex:defaultGrant rdf:reifies <<( ex:alice oldap:hasRole ex:readerRole )>> ;
                          oldap:hasDefaultDataPermission oldap:DATA_VIEW } }""")
        check("Explicit default permission annotation", query("""ASK { GRAPH ex:admin {
          ?grant rdf:reifies <<( ex:alice oldap:hasRole ex:readerRole )>> ;
                 oldap:hasDefaultDataPermission oldap:DATA_VIEW } }""")["boolean"])
        check("Annotations stay in their named graph", not query("""ASK { GRAPH ex:admin {
          ?grant rdf:reifies <<( ex:item oldap:attachedToRole ex:readerRole )>> } }""")["boolean"])
        shorthand = """INSERT DATA { GRAPH ex:shorthand {
          << ex:item oldap:attachedToRole ex:readerRole >> oldap:hasDataPermission oldap:DATA_VIEW } }"""
        update(shorthand)
        update(shorthand)
        short_count = query("SELECT (COUNT(*) AS ?n) WHERE { GRAPH ex:shorthand { ?g rdf:reifies ?t } }")
        check("Repeated anonymous shorthand creates distinct reifiers", short_count["results"]["bindings"][0]["n"]["value"] == "2")
        update("INSERT DATA { " + grants + " }")
        count = query("SELECT (COUNT(*) AS ?n) WHERE { GRAPH ex:data { ?g rdf:reifies ?t } }")
        check("Stable reifier repeated INSERT is idempotent", count["results"]["bindings"][0]["n"]["value"] == "1")
        triple = query("SELECT ?term WHERE { GRAPH ex:data { ex:grant rdf:reifies ?term } }")
        results["triple_term_json"] = triple
        binding = triple["results"]["bindings"][0]["term"]
        check("Triple term JSON result", binding["type"] == "triple")
        update("""INSERT DATA { GRAPH ex:data {
          ex:quoted rdf:reifies <<( ex:unasserted ex:p ex:o )>> ; ex:note "quotation only" . } }""")
        check("Reification does not assert the base triple", not query("ASK { GRAPH ex:data { ex:unasserted ex:p ex:o } }")["boolean"])
        status, turtle = request("/query", urllib.parse.urlencode({"query": PREFIX + "CONSTRUCT { ?s ?p ?o } WHERE { GRAPH ex:data { ?s ?p ?o } }"}).encode(), "application/x-www-form-urlencoded", "text/turtle")
        assert status == 200
        (output / "annotations.ttl").write_bytes(turtle)
        status, response = request("/data?graph=" + urllib.parse.quote("urn:jena-probe:roundtrip", safe=""), turtle, "text/turtle")
        assert 200 <= status < 300, (status, response)
        check("Turtle export/reimport preserves reifier", query("""ASK { GRAPH ex:roundtrip {
          ex:grant rdf:reifies <<( ex:item oldap:attachedToRole ex:readerRole )>> ;
                   oldap:hasDataPermission oldap:DATA_VIEW } }""")["boolean"])
        update("""DELETE DATA { GRAPH ex:admin { ex:alice oldap:hasRole ex:readerRole } }""")
        check("Role revocation removes effective access", not query(permission)["boolean"])
        update("""DELETE { GRAPH ex:data { ex:grant ?p ?o . ex:item oldap:attachedToRole ex:readerRole } }
          WHERE { GRAPH ex:data { ex:grant ?p ?o } }""")
        check("Grant deletion leaves no annotation residue", not query("ASK { GRAPH ex:data { ex:grant ?p ?o } }")["boolean"])

        update("INSERT DATA { GRAPH ex:transaction { ex:committed ex:value 1 } }")
        check("HTTP update visible in a separate request", query("ASK { GRAPH ex:transaction { ex:committed ex:value 1 } }")["boolean"])
        missing = (output / "never-created.ttl").as_uri()
        status, body = request("/update", (PREFIX + "INSERT DATA { GRAPH ex:transaction { ex:rolledBack ex:value 2 } }; LOAD <" + missing + "> INTO GRAPH ex:transaction").encode(), "application/sparql-update")
        results["failed_update_status"] = status
        check("Runtime failure returns an error", status >= 400)
        check("One HTTP update request rolls back all operations", not query("ASK { GRAPH ex:transaction { ex:rolledBack ex:value 2 } }")["boolean"])
        check("Earlier HTTP request is not rolled back", query("ASK { GRAPH ex:transaction { ex:committed ex:value 1 } }")["boolean"])
        status, _ = request("/transactions", b"", "application/octet-stream")
        results["rdf4j_transaction_endpoint_status"] = status
        check("No RDF4J transaction endpoint on stock dataset", status in (404, 405))
        # A false WHERE is a successful no-op, not a transaction abort.
        update('INSERT DATA { GRAPH ex:batch { ex:item ex:revision 1 ; ex:value "original" } }')
        update('''DELETE { GRAPH ex:batch { ex:item ex:revision 99 } }
          INSERT { GRAPH ex:batch { ex:item ex:revision 100 } }
          WHERE { GRAPH ex:batch { ex:item ex:revision 99 } } ;
          INSERT DATA { GRAPH ex:batch { ex:badReceipt ex:state "committed" } }''')
        check("False WHERE does not abort a following unguarded receipt", query(
            'ASK { GRAPH ex:batch { ex:item ex:revision 1 . ex:badReceipt ex:state "committed" } }')["boolean"])
        update("DELETE WHERE { GRAPH ex:batch { ex:badReceipt ?p ?o } }")

        def guarded_change(expected: int, replacement: int, operation: str) -> None:
            """Bind synthetic data, revision and receipt to one common condition.

            This restricted CAS is not a general OLDAP transaction compiler.
            """
            update(f'''DELETE {{ GRAPH ex:batch {{ ex:item ex:revision {expected} ; ex:value ?old }} }}
              INSERT {{ GRAPH ex:batch {{ ex:item ex:revision {replacement} ; ex:value "changed" .
                        ex:{operation} ex:state "committed" }} }}
              WHERE {{ GRAPH ex:batch {{ ex:item ex:revision {expected} ; ex:value ?old }}
                       FILTER NOT EXISTS {{ GRAPH ex:batch {{ ex:{operation} ?p ?o }} }} }}''')

        guarded_change(99, 100, "staleReceipt")
        check("Guarded stale mutation creates no receipt", not query(
            "ASK { GRAPH ex:batch { ex:staleReceipt ?p ?o } }")["boolean"])
        guarded_change(1, 2, "goodReceipt")
        check("One guarded update changes data and records receipt", query(
            'ASK { GRAPH ex:batch { ex:item ex:revision 2 ; ex:value "changed" . ex:goodReceipt ex:state "committed" } }')["boolean"])
        guarded_change(1, 2, "goodReceipt")
        check("Exact synthetic retry leaves one receipt", query(
            "SELECT (COUNT(*) AS ?n) WHERE { GRAPH ex:batch { ex:goodReceipt ?p ?o } }")["results"]["bindings"][0]["n"]["value"] == "1")
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(guarded_change, 2, 3, operation) for operation in ("raceA", "raceB")]
            for future in futures:
                future.result(timeout=20)
        check("Concurrent guarded HTTP mutations have exactly one receipt", query(
            "SELECT (COUNT(*) AS ?n) WHERE { GRAPH ex:batch { VALUES ?r { ex:raceA ex:raceB } ?r ex:state ?s } }")["results"]["bindings"][0]["n"]["value"] == "1")
        check("Concurrent guarded mutations advance the revision only once", query(
            "ASK { GRAPH ex:batch { ex:item ex:revision 3 } }")["boolean"])
        # Receipt queries are separate observation requests, not part of Update's
        # response. Production idempotency additionally needs a request digest.
        from probe_authentication_revocation import run_revocation_checks
        verify_revocation_restart = run_revocation_checks(update, query, check)
        from probe_revocation_connection import run_public_revocation_checks
        run_public_revocation_checks(update, query, check)
        from probe_revocation_authorization import run_authorization_checks
        run_authorization_checks(update, query, check)
        from probe_revocation_recovery import run_recovery_checks
        run_recovery_checks(update, query, check, output, base)
        stop()
        start()
        verify_revocation_restart()
        check("HTTP dataset persists across server restart", query("ASK { GRAPH ex:transaction { ex:committed ex:value 1 } }")["boolean"])
        check("Aborted HTTP writes remain absent after restart", not query("ASK { GRAPH ex:transaction { ex:rolledBack ex:value 2 } }")["boolean"])
        results["status"] = "passed"
    except Exception as error:
        results["status"] = "failed"
        results["error"] = str(error)
        raise
    finally:
        stop()
        (output / "results.json").write_text(json.dumps(results, indent=2) + "\n")


if __name__ == "__main__":
    main()
