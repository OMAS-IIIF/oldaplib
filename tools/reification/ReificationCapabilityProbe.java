import java.io.ByteArrayOutputStream;
import java.nio.file.*;
import org.apache.jena.atlas.json.*;
import org.apache.jena.query.*;
import org.apache.jena.rdf.model.*;
import org.apache.jena.riot.*;
import org.apache.jena.shacl.ShaclValidator;
import org.apache.jena.tdb2.TDB2Factory;
import org.apache.jena.update.UpdateAction;

/** Offline RDF 1.2 capability probe. Only writes to a new caller-owned directory.
 * Args: fixture TriG, output directory. Compiled with the current transfer source.
 * Reports validator support separately from parser/storage/transfer assertions.
 */
public class ReificationCapabilityProbe {
    static final String EX = "https://example.org/reification/";
    static final String SH = "http://www.w3.org/ns/shacl#";
    static final String PREFIX = "PREFIX ex: <" + EX + "> PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> ";
    static int checks;

    /** Fail immediately on a broken capability and emit a readable check name. */
    static void check(boolean value, String label) {
        if (!value) throw new AssertionError(label);
        checks++;
        System.out.println("PASS " + label);
    }

    /** Execute a read query in the transaction supplied by the caller. */
    static boolean ask(Dataset dataset, String pattern) {
        try (var query = QueryExecutionFactory.create(PREFIX + "ASK { " + pattern + " }", dataset)) {
            return query.execAsk();
        }
    }

    /** Produce actual SPARQL JSON, exercising Jena's triple-term encoding. */
    static void results(Dataset dataset, Path path, String queryText) throws Exception {
        try (var query = QueryExecutionFactory.create(PREFIX + queryText, dataset)) {
            var out = new ByteArrayOutputStream();
            ResultSetFormatter.outputAsJSON(out, query.execSelect());
            Files.write(path, out.toByteArray());
        }
    }

    /** Seed only synthetic root/project metadata required by the transfer boundary. */
    static void seed(Dataset dataset) {
        UpdateAction.parseExecute(PREFIX + "PREFIX oldap: <http://oldap.org/base#> INSERT DATA { GRAPH oldap:admin { "
            + "ex:actor oldap:inProject oldap:SystemProject . ex:grant rdf:reifies <<( ex:actor oldap:inProject oldap:SystemProject )>> ; "
            + "oldap:hasAdminPermission oldap:ADMIN_OLDAP . ex:project a oldap:Project ; oldap:projectShortName 'travel' ; "
            + "oldap:namespaceIri <" + EX + "> . } }", dataset);
    }

    public static void main(String[] args) throws Exception {
        if (args.length != 2 || Files.exists(Path.of(args[1])))
            throw new IllegalArgumentException("Expected fixture and new output directory");
        Path out = Files.createDirectory(Path.of(args[1]));
        var report = new JsonObject();
        Dataset source = DatasetFactory.create();
        RDFDataMgr.read(source, args[0]);
        check(ask(source, "GRAPH ex:data { ex:T ex:isAt ex:A . ex:visit1 rdf:reifies <<( ex:T ex:isAt ex:A )>> . "
            + "ex:visit2 rdf:reifies <<( ex:T ex:isAt ex:A )>> }"), "Annotation syntax preserves two reifier identities");
        check(ask(source, "GRAPH ex:shacl { ex:TravelShape <" + SH + "property> ?travel . "
            + "?travel <" + SH + "path> ex:isAt ; <" + SH + "reifierShape> ex:VisitAnnotationShape . "
            + "ex:BuildingShape <" + SH + "property> ?building . ?building <" + SH + "path> ex:isAt . "
            + "FILTER NOT EXISTS { ?building <" + SH + "reifierShape> ?shape } }"),
            "Same predicate has independent shape-use constraints");
        Dataset store = TDB2Factory.connectDataset(out.resolve("tdb").toString());
        store.begin(ReadWrite.WRITE);
        try {
            source.asDatasetGraph().find().forEachRemaining(store.asDatasetGraph()::add);
            seed(store);
            store.commit();
        } finally { store.end(); store.close(); }
        store = TDB2Factory.connectDataset(out.resolve("tdb").toString());
        store.begin(ReadWrite.READ);
        String exported;
        try {
            check(ask(store, "GRAPH ex:data { ex:visit2 rdf:reifies <<( ex:T ex:isAt ex:A )>> ; ex:dateTime ?time }"),
                "TDB2 reopen preserves triple terms");
            results(store, out.resolve("triple-results.json"), "SELECT ?term WHERE { GRAPH ex:data { ex:visit1 rdf:reifies ?term } }");
            results(store, out.resolve("flat-results.json"), "SELECT ?reifier ?value ?time WHERE { GRAPH ex:data { "
                + "ex:T ex:isAt ?value . ?reifier rdf:reifies <<( ex:T ex:isAt ?value )>> ; ex:dateTime ?time } }");
            exported = JenaProjectTransfer.exportGraphs(store, EX + "actor", "{\"project\":\"travel\",\"parts\":[\"onto\",\"shacl\",\"data\"]}");
        } finally { store.end(); store.close(); }
        Dataset imported = DatasetFactory.create();
        seed(imported);
        JsonObject request = JSON.parse("{\"project\":\"travel\",\"parts\":[\"onto\",\"shacl\",\"data\"]}");
        request.put("trig", exported);
        JenaProjectTransfer.importGraphs(imported, EX + "actor", JSON.toString(request));
        for (String part : new String[]{"onto", "shacl", "data"})
            check(source.getNamedModel(EX + part).isIsomorphicWith(imported.getNamedModel(EX + part)), "Native project transfer preserves " + part);

        Model shapes = source.getNamedModel(EX + "shacl");
        Model data = source.getNamedModel(EX + "data");
        var validator = ShaclValidator.get();
        check(validator.conforms(shapes.getGraph(), data.getGraph()), "Jena accepts valid fixture");
        Model invalid = ModelFactory.createDefaultModel().add(data);
        invalid.removeAll(invalid.createResource(EX + "visit1"), invalid.createProperty(EX + "dateTime"), null);
        report.put("jenaRejectsMissingAnnotationField", !validator.conforms(shapes.getGraph(), invalid.getGraph()));
        Model missing = ModelFactory.createDefaultModel().add(data);
        missing.removeAll(null, missing.createProperty("http://www.w3.org/1999/02/22-rdf-syntax-ns#reifies"), null);
        report.put("jenaRejectsMissingReifiers", !validator.conforms(shapes.getGraph(), missing.getGraph()));
        Model targeted = ModelFactory.createDefaultModel().add(shapes);
        targeted.add(targeted.createResource(EX + "VisitAnnotationShape"), targeted.createProperty(SH + "targetNode"), targeted.createResource(EX + "visit1"));
        check(!validator.conforms(targeted.getGraph(), invalid.getGraph()), "Explicit reifier targeting detects missing field");
        Model projection = ModelFactory.createDefaultModel();
        invalid.getGraph().find().forEachRemaining(triple -> {
            if (!triple.getObject().isTripleTerm()) projection.getGraph().add(triple);
        });
        try (var output = Files.newOutputStream(out.resolve("invalid-projection.ttl"))) { RDFDataMgr.write(output, projection, Lang.TURTLE); }
        try (var output = Files.newOutputStream(out.resolve("shapes.ttl"))) { RDFDataMgr.write(output, shapes, Lang.TURTLE); }
        report.put("assertionChecks", checks);
        Files.writeString(out.resolve("native-report.json"), JSON.toString(report) + "\n");
        imported.close(); source.close();
        System.out.println(JSON.toString(report));
    }
}
