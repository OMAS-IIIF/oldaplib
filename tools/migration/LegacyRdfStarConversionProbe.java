import java.nio.file.*;
import java.util.*;
import org.apache.jena.query.*;
import org.apache.jena.riot.*;
import org.apache.jena.sparql.util.IsoMatcher;
import org.apache.jena.tdb2.TDB2Factory;

/** Synthetic conversion acceptance, with optional original GraphDB seed files.
 * Args: new owned TDB2 directory, optional original ontology directory.
 * Never authenticates, starts a server or modifies the original input files.
 */
public class LegacyRdfStarConversionProbe {
    static int checks;
    static final String PREFIX = "@prefix p: <https://example.org/p/> . @prefix oldap: <http://oldap.org/base#> . ";
    static final String QUOTED = "<< p:item oldap:attachedToRole p:Reader >>";
    static final String SOURCE = PREFIX + """
        p:data {
            p:item oldap:attachedToRole p:Reader ; p:label "Quoted << text >>"@de ; p:node _:shared .
            << p:item oldap:attachedToRole p:Reader >> oldap:hasDataPermission oldap:DATA_VIEW .
            << p:item oldap:attachedToRole p:Reader >> p:note "Grüezi" ; oldap:hasDataPermission oldap:DATA_UPDATE .
            << p:orphan oldap:attachedToRole p:Reader >> oldap:hasDataPermission oldap:DATA_VIEW .
        }
        p:lists { _:shared p:name "shared blank node" . }
        p:foreign { << p:item oldap:attachedToRole p:Reader >> oldap:hasDataPermission oldap:DATA_RESTRICTED . }
        """;

    static void check(boolean result, String label) {
        if (!result) throw new AssertionError(label);
        checks++;
        System.out.println("PASS " + label);
    }

    static boolean ask(Dataset data, String pattern) {
        try (QueryExecution query = QueryExecutionFactory.create(
            "PREFIX p: <https://example.org/p/> PREFIX oldap: <http://oldap.org/base#> "
            + "PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> ASK { " + pattern + " }", data)) {
            return query.execAsk();
        }
    }

    static void refuses(String source, String label) throws Exception {
        try (var result = ConvertLegacyRdfStar.convert(source)) {
            throw new AssertionError("Unexpected acceptance: " + label);
        } catch (IllegalArgumentException | RiotException expected) {
            check(true, label);
        }
    }

    /** Verify the scalable matcher rejects identity/value loss, not just counts. */
    static void verifyDatasetComparison() {
        String original = PREFIX + "p:data { p:a p:node _:shared } p:lists { _:shared p:value 1 }";
        String renamed = PREFIX + "p:lists { _:renamed p:value 1 } p:data { p:a p:node _:renamed }";
        List<String> changes = List.of(
            PREFIX + "p:data { p:a p:node _:one } p:lists { _:two p:value 1 }",
            PREFIX + "p:data { p:a p:node _:shared . _:shared p:value 1 }",
            PREFIX + "p:data { p:a p:node _:shared } p:lists { _:shared p:value 2 }",
            PREFIX + "p:data { p:a p:node _:shared } p:lists { _:shared p:other 1 }");
        Dataset expected = DatasetFactory.create(), actual = DatasetFactory.create();
        try {
            RDFParser.fromString(original, Lang.TRIG).parse(expected);
            RDFParser.fromString(renamed, Lang.TRIG).parse(actual);
            check(ConvertLegacyRdfStar.sameDataset(expected, actual), "Verification accepts global blank-node renaming and reordered quads");
            for (String changed : changes) {
                actual.asDatasetGraph().clear();
                RDFParser.fromString(changed, Lang.TRIG).parse(actual);
                check(!ConvertLegacyRdfStar.sameDataset(expected, actual), "Verification rejects split identity or changed graph/value/predicate");
            }
            expected.asDatasetGraph().clear(); actual.asDatasetGraph().clear();
            RDFParser.fromString(PREFIX + "_:g { _:g p:value 1 }", Lang.TRIG).parse(expected);
            RDFParser.fromString(PREFIX + "_:other { _:other p:value 1 }", Lang.TRIG).parse(actual);
            check(ConvertLegacyRdfStar.sameDataset(expected, actual), "Verification preserves blank graph-name identity");
        } finally { expected.close(); actual.close(); }
    }

    public static void main(String[] args) throws Exception {
        verifyDatasetComparison();
        if (args.length < 1 || args.length > 2 || Files.exists(Path.of(args[0])))
            throw new IllegalArgumentException("Expected new owned TDB2 directory and optional original seed directory");
        try (var result = ConvertLegacyRdfStar.convert(SOURCE);
             var again = ConvertLegacyRdfStar.convert(SOURCE)) {
            Dataset data = result.dataset();
            check(IsoMatcher.isomorphic(data.asDatasetGraph(), again.dataset().asDatasetGraph()), "Stable reifier identities on repeated conversion");
            check(result.report().getNumber("ordinaryQuadsPreserved").intValue() == 4,
                  "All four ordinary source quads remain unchanged");
            String reifier = data.getNamedModel("https://example.org/p/data")
                .listSubjectsWithProperty(org.apache.jena.rdf.model.ResourceFactory.createProperty(
                    "http://www.w3.org/1999/02/22-rdf-syntax-ns#reifies")).next().getURI();
            refuses(SOURCE + " <urn:extra> { <urn:x> <" + reifier + "> <urn:y> }",
                    "Generated identity collision with existing predicates refused");
            check(ask(data, "GRAPH p:data { p:item p:label \"Quoted << text >>\"@de ; p:node ?b } GRAPH p:lists { ?b p:name \"shared blank node\" }"),
                  "Literal quotation marks, language and cross-graph blank-node identity preserved");
            check(ask(data, "GRAPH p:data { ?g rdf:reifies <<( p:item oldap:attachedToRole p:Reader )>> ; p:note \"Grüezi\" ; oldap:hasDataPermission oldap:DATA_VIEW, oldap:DATA_UPDATE }"),
                  "Repeated annotations merge permission values and additional metadata");
            check(result.report().getNumber("membershipReifiers").intValue() == 3
                    && result.report().getNumber("orphanedMembershipReifiers").intValue() == 2,
                  "Graph-scoped identity and orphan counts are explicit");
            check(!ask(data, "GRAPH p:data { p:orphan oldap:attachedToRole p:Reader }")
                  && !ask(data, "GRAPH p:foreign { p:item oldap:attachedToRole p:Reader }"), "Conversion never asserts missing memberships");
            Dataset store = TDB2Factory.connectDataset(args[0]);
            try {
                store.begin(ReadWrite.WRITE);
                try { data.asDatasetGraph().find().forEachRemaining(store.asDatasetGraph()::add); store.commit(); }
                finally { store.end(); }
                store.begin(ReadWrite.READ);
                try { check(IsoMatcher.isomorphic(data.asDatasetGraph(), store.asDatasetGraph()), "Converted dataset imports losslessly into owned TDB2"); }
                finally { store.end(); }
            } finally { store.close(); }
        }
        refuses(PREFIX + "p:data { " + QUOTED + " oldap:hasAdminPermission oldap:ADMIN_OLDAP }", "Mismatched permission kind refused");
        refuses(PREFIX + "p:data { p:a p:link " + QUOTED + " }", "Quoted triples as objects refused");
        refuses(PREFIX + "p:data { << " + QUOTED + " p:q p:o >> p:note \"nested\" }", "Nested quoted triples refused");
        refuses(PREFIX + "p:data { << p:a p:unknown p:b >> p:note \"unknown\" }", "Unknown membership predicate refused");
        refuses(PREFIX + "p:data { << _:a oldap:hasRole p:b >> oldap:hasDefaultDataPermission oldap:DATA_VIEW }", "Blank-node membership identity refused");
        refuses(PREFIX + "p:data { p:g <http://www.w3.org/1999/02/22-rdf-syntax-ns#reifies> <<( p:a oldap:hasRole p:b )>> }", "Mixed native RDF 1.2 input refused");
        refuses(PREFIX + "\n#>> {\"userId\":\"example\"}\n", "Serialized user side-channel refused instead of discarded");
        refuses(PREFIX + "p:data { <relative> p:label \"value\" }", "Unbased relative IRI refused");
        refuses(PREFIX + QUOTED + " oldap:hasDataPermission oldap:DATA_VIEW .", "Default-graph permission annotation refused");
        refuses(PREFIX + "p:data { <urn:rdf4j:triple:encoded> oldap:hasDataPermission oldap:DATA_VIEW }", "Encoded RDF4J triple URI refused");
        refuses(PREFIX + "p:data { BROKEN", "Malformed TriG refused");
        try (var plain = ConvertLegacyRdfStar.convert(PREFIX + "p:data { p:a p:value 1 }")) {
            check(plain.report().getNumber("membershipReifiers").intValue() == 0, "Plain RDF needs no generated reifiers");
        }
        if (args.length == 2) {
            for (String name : List.of("admin.trig", "admin-testing.trig")) {
                try (var converted = ConvertLegacyRdfStar.convert(Files.readString(Path.of(args[1]).resolve(name)))) {
                    Dataset nativeSeeds = DatasetFactory.create();
                    try {
                        RDFDataMgr.read(nativeSeeds, "oldaplib/ontologies/" + name);
                        check(JenaSeedOntologyProbe.permissions(nativeSeeds).equals(JenaSeedOntologyProbe.permissions(converted.dataset())),
                            "Original GraphDB " + name + " converts to the migrated seed permission relations");
                    } finally { nativeSeeds.close(); }
                }
            }
        }
        System.out.println("PASS total=" + checks + "; offline only, no inference");
    }
}
