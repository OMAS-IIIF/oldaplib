import java.nio.file.*;
import java.util.*;
import java.util.stream.Collectors;
import org.apache.jena.query.*;
import org.apache.jena.rdf.model.*;
import org.apache.jena.riot.*;

/** Offline native RDF 1.2 seed acceptance; no server, inference or credentials.
 * Arguments: ontology directory, expected-grants TSV, optional pre-migration
 * directory with legacy annotation statements removed. The optional baseline
 * proves that all other administration/model triples are isomorphic unchanged.
 */
public class JenaSeedOntologyProbe {
    static final String RDF = "http://www.w3.org/1999/02/22-rdf-syntax-ns#";
    static final String BASE = "http://oldap.org/base#";
    static final String PREFIX = "PREFIX rdf: <" + RDF + "> PREFIX oldap: <" + BASE + "> ";
    static int checks;

    static void check(boolean ok, String message) {
        if (!ok) throw new AssertionError(message);
        checks++;
        System.out.println("PASS " + message);
    }

    static boolean ask(Dataset data, String body) {
        try (QueryExecution query = QueryExecutionFactory.create(PREFIX + "ASK { GRAPH oldap:admin { " + body + " } }", data)) {
            return query.execAsk();
        }
    }

    static Set<String> permissions(Dataset data) {
        Set<String> rows = new TreeSet<>();
        String sparql = PREFIX + "SELECT ?s ?p ?o ?kind ?permission WHERE { GRAPH oldap:admin { "
            + "?grant rdf:reifies <<( ?s ?p ?o )>> ; ?kind ?permission . "
            + "VALUES ?kind { oldap:hasAdminPermission oldap:hasDefaultDataPermission } } }";
        try (QueryExecution query = QueryExecutionFactory.create(sparql, data)) {
            query.execSelect().forEachRemaining(row -> rows.add(
                List.of("s", "p", "o", "kind", "permission").stream()
                    .map(name -> row.getResource(name).getURI()).collect(Collectors.joining("\t"))));
        }
        return rows;
    }

    static long reifierCount(Dataset data) {
        return data.getNamedModel(BASE + "admin").listSubjectsWithProperty(
            ResourceFactory.createProperty(RDF + "reifies")).toSet().size();
    }

    static void compareBaseline(Path current, Path baseline) {
        Dataset before = DatasetFactory.create(), after = DatasetFactory.create();
        try {
            RDFDataMgr.read(before, baseline.toString());
            RDFDataMgr.read(after, current.toString());
            Model admin = after.getNamedModel(BASE + "admin");
            // Annotation subjects are the only new data; stable reifier IRIs
            // have no other role in these initialization files.
            for (Resource grant : admin.listSubjectsWithProperty(ResourceFactory.createProperty(RDF + "reifies")).toList())
                admin.removeAll(grant, null, null);
            Set<String> names = new HashSet<>();
            before.listNames().forEachRemaining(names::add);
            after.listNames().forEachRemaining(names::add);
            for (String name : names)
                check(before.getNamedModel(name).isIsomorphicWith(after.getNamedModel(name)),
                    current.getFileName() + " preserves ordinary triples in " + name);
            check(before.getDefaultModel().isIsomorphicWith(after.getDefaultModel()), current.getFileName() + " preserves default graph");
        } finally { before.close(); after.close(); }
    }

    public static void main(String[] args) throws Exception {
        if (args.length < 2 || args.length > 3) throw new IllegalArgumentException("ontology directory, manifest, optional baseline required");
        Path root = Path.of(args[0]);
        // Load every supplied syntax independently, including standard vocabularies.
        try (var files = Files.walk(root)) {
            for (Path path : files.filter(Files::isRegularFile).sorted().toList()) {
                String name = path.getFileName().toString();
                if (!(name.endsWith(".trig") || name.endsWith(".ttl") || name.endsWith(".xml"))) continue;
                Dataset parsed = DatasetFactory.create();
                try {
                    if (name.endsWith(".xml")) RDFDataMgr.read(parsed.getDefaultModel(), path.toString(), Lang.RDFXML);
                    else RDFDataMgr.read(parsed, path.toString());
                    check(!parsed.isEmpty(), "Native Jena parses " + root.relativize(path));
                } finally { parsed.close(); }
            }
        }
        Dataset seeds = DatasetFactory.create();
        try {
            for (String name : List.of("oldap.trig", "shared.trig", "admin.trig", "admin-testing.trig"))
                RDFDataMgr.read(seeds, root.resolve(name).toString());
            Set<String> expected = Files.readAllLines(Path.of(args[1])).stream()
                .filter(line -> !line.isBlank() && !line.startsWith("#")).collect(Collectors.toSet());
            check(expected.size() == 29 && permissions(seeds).equals(expected), "All 29 original permission values preserved");
            check(reifierCount(seeds) == 18, "18 distinct membership reifiers, including merged duplicate annotation");
            check(!ask(seeds, "?grant rdf:reifies <<( ?s ?p ?o )>> . FILTER NOT EXISTS { ?s ?p ?o }"),
                "Every grant retains its separately asserted membership");
            check(!ask(seeds, "?grant rdf:reifies ?a, ?b . FILTER (?a != ?b)"), "No reifier describes two different memberships");
            check(!ask(seeds, "?grant rdf:reifies ?term . FILTER (!isIRI(?grant))"), "All seed reifiers have stable IRIs");
            for (String name : List.of("admin.trig", "admin-testing.trig")) RDFDataMgr.read(seeds, root.resolve(name).toString());
            check(reifierCount(seeds) == 18 && permissions(seeds).equals(expected), "Reload does not duplicate permission reifiers or values");
            if (args.length == 3)
                for (String name : List.of("admin.trig", "admin-testing.trig"))
                    compareBaseline(root.resolve(name), Path.of(args[2]).resolve(name));
        } finally { seeds.close(); }
        System.out.println("PASS total=" + checks + "; no reasoner or external service used");
    }
}
