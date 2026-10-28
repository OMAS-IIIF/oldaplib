# J0: isolated Jena/Fuseki capability probe

Date: 2026-10-27. Outcome: synthetic capability probes pass; the remote transaction
architecture remains to be selected. No OLDAP application code was changed.

## Installed and executed

- Apache Jena Fuseki 6.2.0, official binary distribution.
- Existing Homebrew OpenJDK 25.0.2, arm64; no global Java configuration changed.
- Installation: `~/Library/Application Support/OLDAP-Jena/apache-jena-fuseki-6.2.0`.
- Download SHA512 verified against Apache's published checksum:
  `ba65f5867d2d4741b2ed9e2af5a0d4fbb447909894ab2a0c6bc4dac8997f4fe339c87b13c48d45d054977769f0f8bf763ea346b1f7792d5cdc458041bd43a132`.
- Test server: loopback only, port 3031, dataset `/probe`, 512 MiB Java heap cap.
- Separate fresh TDB2 directories for the Java and HTTP probes.
- Synthetic data only, with no OLDAP/Redis connections, credentials or fixtures.
- Server stopped after testing. No login service or autostart installed.

[Machine-readable results](j0-results.json) record the Java version, JAR hash,
checks, response statuses and actual triple-term JSON response. Complete logs and
data are retained outside Git under
`~/Library/Application Support/OLDAP-Jena/probes/j0-20261027-03/`.

The initial run expected 404 for an unavailable transaction endpoint; Fuseki
actually returns 405 with `No Fuseki dispatch /probe/transactions` in its log.
The probe now accepts either unavailable-route response. A subsequent start
preflight encountered TIME_WAIT from the stopped server; SO_REUSEADDR permits
that state while retaining the port-availability check. The final complete run
passed. Earlier logs remain in run directories 01/02; 03 is the acceptance run.

## Results and what they establish

### TDB2 inside the Java process

`JenaTransactionProbe.java` exercises the real TDB2 transaction API:

- Reads inside the writer see earlier uncommitted writes.
- A reader on another thread sees none of the uncommitted facts.
- Abort removes both the synthetic resource and its receipt.
- Commit makes both facts visible.
- Two concurrent read/check/write claim transactions produce exactly one winner.
- Closing and reopening the dataset retains committed data.

These tests establish the required basic storage primitives. They do not establish
that a Python process can hold the same transaction across HTTP requests, nor do
they prove OLDAP recovery, crash durability or throughput.

### Unmodified Fuseki over HTTP

- A committed update is visible to a subsequent query.
- A request containing INSERT followed by a failing LOAD returns HTTP 400 and
  leaves none of that request's inserted facts. The LOAD targets a nonexistent
  file in the private test directory; this tests an execution failure, not merely
  invalid syntax.
- A previously committed request remains committed despite that later failure.
- POST `/probe/transactions` returns 405 and no dispatch route; it does not create
  a GraphDB/RDF4J-style transaction session.
- After a graceful server restart, committed facts remain and aborted facts do not.

Conclusion: atomicity of one HTTP update request is usable. It cannot directly
implement OLDAP's current Python read/query/update/commit sequence. A client-side
Redis gate cannot turn independently committed requests into a rollback-capable
transaction. This test verifies the stock configuration and conventional endpoint;
it is not an exhaustive search for all possible server extensions.

### RDF 1.2 annotations

The explicit representation works for all three permission patterns:

```turtle
@prefix ex: <urn:jena-probe:> .
@prefix oldap: <http://oldap.org/base#> .
@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .

ex:item oldap:attachedToRole ex:readerRole .
ex:grant rdf:reifies <<( ex:item oldap:attachedToRole ex:readerRole )>> ;
    oldap:hasDataPermission oldap:DATA_VIEW .
```

Tests cover resource permission joins through a user's role, project admin
permissions, explicit role defaults, absence of invented defaults, graph scope,
revocation and annotation cleanup. These are representative query patterns, not
execution of the unmodified OLDAP authorization stack.

Two identity tests are particularly important:

- Repeating INSERT with the same explicit reifier IRI retains one reifier.
- Repeating the old-looking anonymous `<< s p o >> annotation value` form creates
  **two distinct reifiers** in Jena 6.2.0. Parsing succeeds, but this does not retain
  the old quoted-triple identity assumption.

The test also confirms that reification alone does not assert its base triple.
Turtle CONSTRUCT export and Graph Store reimport preserve the explicit annotation.
A selected triple term is returned as `type: triple`, with nested
`subject`, `predicate` and `object` fields. OLDAP's QueryProcessor must either
support this representation explicitly or keep such terms internal to the query
and return scalar bindings. JSON-LD and all other serialization paths remain open.

No SHACL validator or inference engine was enabled. SHACL remains model metadata.

## Reproduce

Run from the Jena oldaplib checkout with a new output directory each time:

```sh
.venv/bin/python tools/migration/probe_jena.py \
  --fuseki-home "$HOME/Library/Application Support/OLDAP-Jena/apache-jena-fuseki-6.2.0" \
  --output "$HOME/Library/Application Support/OLDAP-Jena/probes/my-new-run"
```

The runner uses only Python's standard library and the Fuseki distribution JAR.
Java source-file launching avoids Maven installation. It refuses an existing run
directory and restricts ports to 3031–3039. It starts its own process, performs
checks, restarts that process once, then stops it in a finally block. It does not
accept an arbitrary remote endpoint. Use `--java /path/to/java` to pin the JVM.
Checks use assertions: do not run Python with `-O` or PYTHONOPTIMIZE.

Downloads used:

- [Official binary](https://dlcdn.apache.org/jena/binaries/apache-jena-fuseki-6.2.0.tar.gz)
- [Official checksum](https://downloads.apache.org/jena/binaries/apache-jena-fuseki-6.2.0.tar.gz.sha512)

Artifacts are checksum-verified; PGP signature verification was not performed.

## Next decision, before broader implementation

RDF 1.2 looks suitable for the tested annotation patterns. Explicit reifier
identity is the working direction; allocation, uniqueness, nested annotations,
full data conversion and comprehensive permission parity still require design.

The larger decision concerns where a complete transaction executes:

1. A server-side command can perform all steps in one Jena transaction, but
   existing Python decisions/hooks must be mapped deliberately.
2. A multi-request transaction extension can preserve that Python workflow, but
   requires maintained session ownership, bounded lifetimes, thread affinity,
   cancellation and uncertain-commit recovery. Holding TDB2's writer between
   requests also needs a bounded performance test.

Next bounded step: trace one real OLDAP resource operation plus its receipt hook,
then design both mappings and choose the smallest sustainable solution. Do not
implement a broad transport adapter or rewrite application logic before recording
that decision. No inference, full-text, live-data conversion or cutover work is
implied by this successful capability probe.
