import java.nio.file.*;
import java.util.*;
import org.apache.jena.graph.NodeFactory;
import org.apache.jena.query.*;
import org.apache.jena.query.text.*;
import org.apache.jena.tdb2.TDB2Factory;
import org.apache.jena.update.UpdateAction;
import org.apache.lucene.analysis.standard.StandardAnalyzer;
import org.apache.lucene.store.FSDirectory;

/** Owned-dataset capability probe, not production connector configuration.
 * Uses one document per RDF literal, explicit graph/language/UID fields and
 * StandardAnalyzer. Every check is executed against the bundled Jena runtime.
 */
public class JenaTextProbe {
    static final String PREFIX = "PREFIX ex: <urn:probe:> PREFIX text: <http://jena.apache.org/text#> "
        + "PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> ";
    static final List<String> checks = new ArrayList<>();

    static Dataset open(Path root) throws Exception {
        EntityDefinition mapping = new EntityDefinition("uri", "title", NodeFactory.createURI("urn:probe:title"));
        mapping.set("body", NodeFactory.createURI("urn:probe:body"));
        mapping.setGraphField("graph");
        mapping.setLangField("lang");
        // Required to remove exactly the indexed document for a deleted quad.
        mapping.setUidField("uid");
        TextIndexConfig config = new TextIndexConfig(mapping);
        config.setAnalyzer(new StandardAnalyzer());
        config.setValueStored(true);
        return TextDatasetFactory.createLucene(TDB2Factory.connectDataset(root.resolve("tdb").toString()),
            FSDirectory.open(root.resolve("index")), config);
    }

    static void update(Dataset ds, String update, boolean commit) {
        ds.begin(ReadWrite.WRITE);
        try {
            UpdateAction.parseExecute(PREFIX + update, ds);
            if (commit) ds.commit(); else ds.abort();
        } finally { ds.end(); }
    }

    static List<String> rows(Dataset ds, String query) {
        ds.begin(ReadWrite.READ);
        try (QueryExecution execution = QueryExecutionFactory.create(PREFIX + query, ds)) {
            List<String> values = new ArrayList<>();
            ResultSet results = execution.execSelect();
            while (results.hasNext()) values.add(results.next().get("s").toString());
            return values;
        } finally { ds.end(); }
    }

    static int count(Dataset ds, String pattern) {
        ds.begin(ReadWrite.READ);
        try (QueryExecution execution = QueryExecutionFactory.create(PREFIX
                + "SELECT (COUNT(DISTINCT ?s) AS ?count) WHERE { " + pattern + " }", ds)) {
            return execution.execSelect().next().getLiteral("count").getInt();
        } finally { ds.end(); }
    }

    static String text(String property, String expression) {
        // Probe expressions are fixed literals, not user-controlled input.
        return "GRAPH ex:data { (?s ?score) text:query (ex:" + property + " '" + expression + "') }";
    }

    static Set<String> hits(Dataset ds, String pattern) {
        return new HashSet<>(rows(ds, "SELECT DISTINCT ?s WHERE { " + pattern + " }"));
    }

    static void check(String label, boolean condition) {
        if (!condition) throw new AssertionError(label);
        checks.add(label);
        System.out.println("PASS " + label);
    }

    static Set<String> ids(String... names) {
        Set<String> result = new HashSet<>();
        for (String name : names) result.add("urn:probe:" + name);
        return result;
    }

    public static void main(String[] args) throws Exception {
        Path root = Path.of(args[0]);
        // Never open or alter an existing user dataset/index on the initial run.
        Files.createDirectory(root);
        Dataset ds = open(root);
        try {
            update(ds, """
                INSERT DATA {
                  GRAPH ex:data {
                    ex:cat ex:title "Red fox", "Fox portrait" ; ex:body "Forest animal" ; ex:role ex:reader .
                    ex:grant rdf:reifies <<( ex:cat ex:role ex:reader )>> ; ex:permission ex:view .
                    ex:second ex:title "Blue fox" ; ex:body "River animal" ; ex:role ex:reader .
                    ex:grant2 rdf:reifies <<( ex:second ex:role ex:reader )>> ; ex:permission ex:view .
                    ex:private ex:title "Fox fox fox" ; ex:role ex:stranger .
                    ex:grant3 rdf:reifies <<( ex:private ex:role ex:stranger )>> ; ex:permission ex:view .
                    ex:orphan ex:title "Fox" .
                    ex:grant4 rdf:reifies <<( ex:orphan ex:role ex:reader )>> ; ex:permission ex:view .
                    ex:restricted ex:title "Fox" ; ex:role ex:reader .
                    ex:grant5 rdf:reifies <<( ex:restricted ex:role ex:reader )>> ; ex:permission ex:restrictedPermission .
                    ex:language ex:title "Grüne Wälder"@de .
                  }
                  GRAPH ex:other { ex:cat ex:title "SecretOnly" . ex:outside ex:title "Fox" . }
                  GRAPH ex:admin { ex:user ex:member ex:reader . ex:view ex:value 2 . ex:restrictedPermission ex:value 1 . }
                }
                """, true);
            check("Committed literals are indexed with graph isolation", hits(ds, text("title", "fox"))
                .equals(ids("cat", "second", "private", "orphan", "restricted")));
            check("Case-insensitive token search", hits(ds, text("title", "RED")).equals(ids("cat")));
            check("Phrase search", hits(ds, text("title", "\"red fox\"")).equals(ids("cat")));
            check("Wildcard search", hits(ds, text("title", "blu*")).equals(ids("second")));
            check("Boolean query within one literal", hits(ds, text("title", "red AND fox")).equals(ids("cat")));
            check("Other graph cannot supply matching text for same subject", hits(ds, text("title", "SecretOnly")).isEmpty());
            check("Language-tag restriction", hits(ds, "GRAPH ex:data { ?s text:query (ex:title 'wälder' 'lang:de') }")
                .equals(ids("language")));
            check("Wrong language does not match", hits(ds, "GRAPH ex:data { ?s text:query (ex:title 'wälder' 'lang:en') }").isEmpty());
            check("StandardAnalyzer does not promise accent folding", hits(ds, text("title", "walder")).isEmpty());
            check("Default triple documents cannot satisfy raw cross-field AND",
                hits(ds, text("title", "title:red AND body:forest")).isEmpty());
            check("Independent text joins implement entity-level field AND",
                hits(ds, text("title", "red").replace("?score", "?titleScore") + text("body", "forest").replace("?score", "?bodyScore"))
                .equals(ids("cat")));
            check("Default documents do not combine two values of the same field",
                hits(ds, text("title", "red AND portrait")).isEmpty());
            check("Independent joins can combine two values of one field",
                hits(ds, text("title", "red").replace("?score", "?firstScore") + text("title", "portrait").replace("?score", "?secondScore"))
                .equals(ids("cat")));
            check("Field OR can use an explicit union", hits(ds, "{ " + text("title", "red") + " } UNION { " + text("body", "river") + " }")
                .equals(ids("cat", "second")));
            String access = """
                GRAPH ex:admin { ex:user ex:member ?role . ?permission ex:value ?value . FILTER(?value >= 2) }
                GRAPH ex:data { ?s ex:role ?role . ?grant rdf:reifies <<( ?s ex:role ?role )>> ; ex:permission ?permission }
                """;
            String visible = text("title", "fox") + access;
            check("RDF 1.2 ACL excludes denied, orphan and below-threshold hits", hits(ds, visible).equals(ids("cat", "second")));
            check("Distinct count does not count multiple matching literals", count(ds, visible) == 2);
            check("Permissions precede final page without an early text limit", rows(ds,
                "SELECT DISTINCT ?s WHERE { " + visible + " } ORDER BY STR(?s) LIMIT 1 OFFSET 1").equals(List.of("urn:probe:second")));
            update(ds, "INSERT DATA { GRAPH ex:data { ex:aborted ex:title 'RollbackMarker' } }", false);
            check("Rolled-back insertion leaves no text hit", hits(ds, text("title", "RollbackMarker")).isEmpty());
            update(ds, "DELETE DATA { GRAPH ex:data { ex:cat ex:title 'Red fox' } }", false);
            check("Rolled-back deletion retains text hit", hits(ds, text("title", "red")).equals(ids("cat")));
            update(ds, "DELETE DATA { GRAPH ex:data { ex:cat ex:title 'Red fox' } }; INSERT DATA { GRAPH ex:data { ex:cat ex:title 'Golden hare' } }", true);
            check("Committed replacement removes old text", hits(ds, text("title", "red")).isEmpty());
            check("Committed replacement indexes new text", hits(ds, text("title", "golden")).equals(ids("cat")));
            update(ds, "DELETE DATA { GRAPH ex:data { ex:second ex:title 'Blue fox' } }", true);
            check("Committed deletion removes its index document", hits(ds, text("title", "blue")).isEmpty());
            ds.close();
            ds = open(root);
            check("Clean reopen preserves committed index", hits(ds, text("title", "golden")).equals(ids("cat")));
            check("Clean reopen preserves deletions and rollback", hits(ds, text("title", "blue OR RollbackMarker")).isEmpty());
            // Persist only after all checks succeed. This probe does not claim
            // crash atomicity between TDB2 and the separate Lucene files.
            String json = "{\"status\":\"passed\",\"checks\":[" + String.join(",", checks.stream().map(x -> "\"" + x + "\"").toList()) + "]}\n";
            Files.writeString(root.resolve("results.json"), json);
        } finally { ds.close(); }
    }
}
