import java.io.*;
import java.nio.file.*;
import java.util.*;
import org.apache.jena.atlas.json.*;
import org.apache.jena.graph.*;
import org.apache.jena.query.*;
import org.apache.jena.query.text.*;
import org.apache.jena.query.text.changes.TextQuadAction;
import org.apache.lucene.store.FSDirectory;

/** Builds the probe index from normalized project configuration, not field names.
 * Python validates one YAML source for both query paths and index predicates.
 * Only terminal text predicates are indexed; links are traversed at query time.
 */
public final class JenaTextFixture {
    static Dataset attach(Dataset storage, Path directory) {
        try {
            String source = System.getenv("PROBE_TEXT_CONFIG");
            if (source == null) throw new IllegalArgumentException("Missing project text configuration");
            JsonArray projects = JSON.parseAny(Files.readString(Path.of(source))).getAsArray();
            Index owned = open(projects, directory);
            return TextDatasetFactory.create(storage, owned.index, true, owned.producer);
        } catch (IOException error) { throw new UncheckedIOException(error); }
    }

    /** One owned index, reused for live writes and a full RDF snapshot rebuild. */
    static final class Index implements AutoCloseable {
        final TextIndex index;
        final TextDocProducer producer;
        Index(TextIndex index, TextDocProducer producer) { this.index = index; this.producer = producer; }
        Dataset attach(Dataset storage) { return TextDatasetFactory.create(storage, index, false, producer); }
        @Override public void close() { index.close(); }
    }

    static Index open(JsonArray projects, Path directory) {
        try {
            Map<Node, Set<Node>> allowed = new HashMap<>();
            Set<Node> predicates = new LinkedHashSet<>();
            for (JsonValue value : projects) {
                JsonObject project = value.getAsObject();
                Node graph = NodeFactory.createURI(project.getString("graph"));
                if (graph.getURI().equals(JenaSessionEngine.RECEIPTS)
                        || graph.getURI().equals("http://oldap.org/base#admin"))
                    throw new IllegalArgumentException("Private metadata cannot be indexed");
                Set<Node> properties = allowed.computeIfAbsent(graph, key -> new HashSet<>());
                project.getArray("predicates").forEach(item -> {
                    Node property = NodeFactory.createURI(item.getAsString().value());
                    properties.add(property);
                    predicates.add(property);
                });
            }
            if (predicates.isEmpty()) throw new IllegalArgumentException("No text predicates configured");
            EntityDefinition fields = new EntityDefinition("uri", "field0", predicates.iterator().next());
            int number = 0;
            for (Node predicate : predicates) fields.set("field" + number++, predicate);
            fields.setUidField("uid");
            fields.setGraphField("graph");
            fields.setLangField("lang");
            TextIndexConfig config = new TextIndexConfig(fields);
            config.setAnalyzer(new OldapTextAnalyzer());
            TextIndex index = TextDatasetFactory.createLuceneIndex(FSDirectory.open(directory), config);
            TextDocProducer producer = new TextDocProducerTriples(index) {
                @Override public void change(TextQuadAction action, Node graph, Node subject, Node predicate, Node object) {
                    // An index can bypass graph views. Require an explicit
                    // project/predicate pair before any document enters it.
                    if (allowed.getOrDefault(graph, Set.of()).contains(predicate))
                        super.change(action, graph, subject, predicate, object);
                }
            };
            return new Index(index, producer);
        } catch (IOException error) { throw new UncheckedIOException(error); }
    }
}
