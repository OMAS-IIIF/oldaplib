"""Run isolated stage 1A probes against the pinned Jena and Python dependencies.

No server, Redis connection, or live project is used. The output directory must
not exist. Compilation and TDB2 storage stay inside it; evidence is JSON.
Run with the repository virtualenv and --help for required local runtime paths.
"""

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace
from functools import partial

import pyshacl
import rdflib
from rdflib import Graph, Namespace, URIRef

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from oldaplib.src.helpers.context import Context
from oldaplib.src.helpers.query_processor import QueryProcessor
from oldaplib.src.xsd.xsd_datetime import Xsd_dateTime
from oldaplib.src.objectfactory import ResourceInstance
from oldaplib.src.helpers.oldaperror import OldapErrorValue


def check_oldap_validation() -> None:
    """Exercise existing per-set validation without constructing a live resource.

    The scope and constraint descriptor supply only the fields used by the
    existing method. This is a reuse probe, not a new validation implementation.
    Datatype construction is deliberately tested separately from cardinality.
    """
    scope = SimpleNamespace(name="visit", _values={})
    scope.validate_value = partial(ResourceInstance.validate_value, scope)
    prop = SimpleNamespace(minCount=1, maxCount=1, get=lambda key: None)
    validate = partial(ResourceInstance._ResourceInstance__validate_property_set,
                       scope, prop_iri="ex:dateTime", prop=prop)
    first = Xsd_dateTime("2026-11-13T09:00:00+01:00")
    second = Xsd_dateTime("2026-11-13T18:00:00+01:00")
    validate({first})
    for invalid in (set(), {first, second}):
        try:
            validate(invalid)
        except OldapErrorValue:
            pass
        else:
            raise AssertionError("Existing cardinality validation accepted invalid annotation")
    try:
        Xsd_dateTime("not-a-date")
    except (OldapErrorValue, ValueError):
        pass
    else:
        raise AssertionError("Existing datatype constructor accepted invalid date")


def run(java_home: Path, service_lib: Path, output: Path) -> dict:
    """Compile/run native checks and inspect validation and result decoding.

    Args:
        java_home: JDK 25 installation root.
        service_lib: Existing service lib directory containing both service and
            pinned Fuseki jars. Used read-only for compilation/runtime classes.
        output: New directory for compiled classes, owned storage, and evidence.

    Returns:
        Capability observations and successful assertion counts.

    Raises:
        ValueError: The Fuseki dependency differs from the reviewed build.
        FileExistsError: Output exists.
        AssertionError: A required baseline or traversal check fails.
        subprocess.CalledProcessError: Compilation or native checks fail.
    """
    jar_hash = hashlib.sha256((service_lib / "fuseki-server.jar").read_bytes()).hexdigest()
    if jar_hash != "2c92c598e65ab69d99820052e05f4277ed1d77980a8845f87545ad35b71a76ee":
        raise ValueError("Expected reviewed Fuseki 6.2.0 jar")
    output.mkdir(parents=True, exist_ok=False)
    classes = output / "classes"
    classes.mkdir()
    classpath = str(service_lib / "*")
    subprocess.run([
        str(java_home / "bin/javac"), "--release", "25", "-cp", classpath,
        "-d", str(classes), str(ROOT / "tools/reification/ReificationCapabilityProbe.java"),
        str(ROOT / "tools/migration/JenaProjectTransfer.java"),
    ], check=True)
    fixture = ROOT / "oldaplib/testdata/reification/travel.trig"
    native = output / "native"
    subprocess.run([
        str(java_home / "bin/java"), "-cp", str(classes) + ":" + classpath,
        "ReificationCapabilityProbe", str(fixture), str(native),
    ], check=True)
    report = json.loads((native / "native-report.json").read_text())
    context = Context(name="REIFICATION_CAPABILITY_PROBE")
    flat = QueryProcessor(context, json.loads((native / "flat-results.json").read_text()))
    assert len(flat) == 3 and all(set(row) == {"reifier", "value", "time"} for row in flat)
    assert len({str(row["reifier"]) for row in flat}) == 3
    assert all(isinstance(row["time"], Xsd_dateTime) for row in flat)
    term_result = json.loads((native / "triple-results.json").read_text())
    report["nativeTripleBindingType"] = term_result["results"]["bindings"][0]["term"]["type"]
    try:
        decoded = QueryProcessor(context, term_result)
        report["queryProcessorPreservesTripleBinding"] = "term" in decoded[0]
    except (KeyError, ValueError, TypeError) as error:
        report["queryProcessorPreservesTripleBinding"] = False
        report["queryProcessorTripleError"] = type(error).__name__
    report["flatBindingsDecoded"] = len(flat)

    shapes = Graph().parse(native / "shapes.ttl")
    data = Graph().parse(native / "invalid-projection.ttl")
    report["pyshaclRejectsMissingReifiers"] = not pyshacl.validate(data, shacl_graph=shapes)[0]
    sh = Namespace("http://www.w3.org/ns/shacl#")
    ex = Namespace("https://example.org/reification/")
    shapes.add((ex.VisitAnnotationShape, sh.targetNode, ex.visit1))
    assert not pyshacl.validate(data, shacl_graph=shapes)[0]
    report["pyshaclExplicitTargetRejectsMissingField"] = True
    data.add((ex.visit1, ex.dateTime, rdflib.Literal("2026-11-13T09:00:00+01:00", datatype=URIRef("http://www.w3.org/2001/XMLSchema#dateTime"))))
    assert pyshacl.validate(data, shacl_graph=shapes)[0]
    report["pyshaclExplicitTargetAcceptsValidField"] = True
    report["pythonAssertionChecks"] = 5
    check_oldap_validation()
    report["oldapValidationChecks"] = 4
    report["versions"] = {"rdflib": rdflib.__version__, "pyshacl": pyshacl.__version__, "fuseki": "6.2.0"}
    report["fusekiSha256"] = jar_hash
    report["fixtureSha256"] = hashlib.sha256(fixture.read_bytes()).hexdigest()
    report["sourceSha256"] = {
        str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in (Path(__file__), ROOT / "tools/reification/ReificationCapabilityProbe.java",
                     ROOT / "tools/migration/JenaProjectTransfer.java")
    }
    report["scope"] = "Offline synthetic data; current transfer source; no HTTP, Redis, or live instance writes"
    (output / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--java-home", type=Path, required=True)
    parser.add_argument("--service-lib", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    run(args.java_home.resolve(), args.service_lib.resolve(), args.output.resolve())
