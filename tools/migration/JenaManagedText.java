import java.io.*;
import java.net.URI;
import java.nio.ByteBuffer;
import java.nio.channels.FileChannel;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.util.*;
import org.apache.jena.atlas.json.*;
import org.apache.jena.query.*;
import org.apache.jena.query.text.changes.TextQuadAction;
import org.apache.jena.sparql.core.Quad;

/** Durable configuration and rebuild lifecycle for the isolated migration service.
 *
 * RDF is authoritative. Each startup rebuilds before listening, avoiding reliance
 * on crash atomicity between TDB2 and Lucene. The engine serializes administration
 * with writers and excludes readers during replacement. No user-supplied path is
 * used on disk. The manifest is the sole durable configuration authority.
 */
final class JenaManagedText implements AutoCloseable {
    final Dataset storage;
    final Path root;
    JsonObject projects = new JsonObject();
    JenaTextFixture.Index current;
    Path directory;
    volatile boolean unavailable;

    JenaManagedText(Dataset storage, Path root) throws IOException {
        this.storage = storage;
        this.root = root;
        Files.createDirectories(root);
        Path manifest = root.resolve("configuration.json");
        if (Files.exists(manifest)) {
            JsonObject saved = JSON.parse(Files.readString(manifest));
            exact(saved, Set.of("version", "projects"));
            if (saved.getNumber("version").intValue() != 1) throw new IOException("Unsupported text configuration version");
            projects = saved.getObj("projects");
            for (String project : projects.keys()) {
                name(project);
                JsonObject entry = projects.getObj(project);
                exact(entry, Set.of("revision", "configuration"));
                UUID.fromString(entry.getString("revision"));
                configuration(entry.getObj("configuration"));
            }
            uniqueGraphs(projects);
        }
        // Indexes are derived data owned by this component. Never open an index
        // left by a killed writer, even when its configuration has not changed.
        try (var entries = Files.list(root)) {
            for (Path path : entries.filter(p -> p.getFileName().toString().startsWith("index-")).toList())
                removeIndex(path);
        }
        if (!projects.isEmpty()) {
            Candidate candidate = rebuild(projects);
            current = candidate.index();
            directory = candidate.directory();
        }
    }

    static void exact(JsonObject value, Set<String> keys) {
        if (!value.keys().equals(keys)) throw new JenaSessionEngine.Refusal(400, "Unexpected fulltext configuration keys");
    }
    @SuppressWarnings("removal")
    static void name(String value) {
        if (value == null || !org.apache.jena.util.XMLChar.isValidNCName(value))
            throw new JenaSessionEngine.Refusal(400, "Invalid project or field name");
    }
    static void iri(String value) {
        if (value == null || !(value.startsWith("https://") || value.startsWith("http://") || value.startsWith("urn:"))
                || !URI.create(value).isAbsolute() || value.chars().anyMatch(c -> c <= 32 || c == '<' || c == '>'))
            throw new JenaSessionEngine.Refusal(400, "Expected an absolute predicate or graph IRI");
    }

    /** Accept only the portable, fully resolved configuration; no native options. */
    static JsonObject configuration(JsonObject config) {
        exact(config, Set.of("graph", "fields"));
        String graph = config.getString("graph");
        iri(graph);
        if (!graph.endsWith("data") || graph.equals(JenaSessionEngine.RECEIPTS))
            throw new JenaSessionEngine.Refusal(400, "Only explicit project data graphs may be indexed");
        JsonObject fields = config.getObj("fields");
        if (fields.isEmpty() || fields.size() > 256)
            throw new JenaSessionEngine.Refusal(400, "Expected 1..256 fulltext fields");
        JsonObject normalized = new JsonObject();
        for (String field : new TreeSet<>(fields.keys())) {
            name(field);
            JsonArray path = fields.get(field).getAsArray();
            if (path.isEmpty() || path.size() > 16) throw new JenaSessionEngine.Refusal(400, "Expected 1..16 predicates per field");
            path.forEach(p -> iri(p.getAsString().value()));
            normalized.put(field, path);
        }
        JsonObject result = new JsonObject();
        result.put("graph", graph);
        result.put("fields", normalized);
        return result;
    }

    static void uniqueGraphs(JsonObject projects) {
        Set<String> graphs = new HashSet<>();
        for (JsonValue entry : projects.values())
            if (!graphs.add(entry.getAsObject().getObj("configuration").getString("graph")))
                throw new JenaSessionEngine.Refusal(409, "Data graph already belongs to another fulltext project");
    }

    Dataset dataset() { return current == null ? storage : current.attach(storage); }

    String state(String project) {
        name(project);
        JsonObject result = new JsonObject();
        result.put("project", project);
        JsonObject entry = projects.hasKey(project) ? projects.getObj(project) : null;
        result.put("configuration", entry == null ? JsonNull.instance : entry.get("configuration"));
        result.put("revision", entry == null ? JsonNull.instance : entry.get("revision"));
        result.put("status", entry == null ? "absent" : "active");
        return JSON.toString(result);
    }

    /** Bind a compiled search to the configuration used to resolve its fields.
     * The engine holds the read lock through validation AND query execution.
     */
    String checkedQuery(String body) {
        JsonObject request = JSON.parse(body);
        exact(request, Set.of("project", "revision", "query"));
        String project = request.getString("project");
        name(project);
        if (!projects.hasKey(project) || !projects.getObj(project).get("revision").equals(request.get("revision")))
            throw new JenaSessionEngine.Refusal(409, "Fulltext configuration changed; resolve fields again");
        return request.getString("query");
    }

    record Candidate(JenaTextFixture.Index index, Path directory) {}

    /** Build only allowed project/predicate quads from one committed RDF snapshot. */
    Candidate rebuild(JsonObject desired) throws IOException {
        JsonArray definitions = new JsonArray();
        for (String project : new TreeSet<>(desired.keys())) {
            JsonObject config = desired.getObj(project).getObj("configuration");
            Set<String> predicates = new TreeSet<>();
            config.getObj("fields").values().forEach(value -> {
                JsonArray path = value.getAsArray();
                predicates.add(path.get(path.size() - 1).getAsString().value());
            });
            JsonArray values = new JsonArray();
            predicates.forEach(values::add);
            JsonObject definition = new JsonObject();
            definition.put("graph", config.getString("graph"));
            definition.put("predicates", values);
            definitions.add(definition);
        }
        Path target = root.resolve("index-" + UUID.randomUUID());
        JenaTextFixture.Index index = null;
        try {
            index = JenaTextFixture.open(definitions, target);
            storage.begin(ReadWrite.READ);
            try {
                index.producer.start();
                var quads = storage.asDatasetGraph().find();
                try {
                    while (quads.hasNext()) {
                        Quad q = quads.next();
                        index.producer.change(TextQuadAction.ADD, q.getGraph(), q.getSubject(), q.getPredicate(), q.getObject());
                    }
                } finally { org.apache.jena.atlas.iterator.Iter.close(quads); }
                index.producer.finish();
                index.index.prepareCommit();
                index.index.commit();
            } finally { storage.end(); }
            return new Candidate(index, target);
        } catch (Exception error) {
            if (index != null) index.close();
            removeIndex(target);
            throw error;
        }
    }

    /** Compare, build, publish configuration, then swap. Caller holds maintenance. */
    String apply(JsonObject request, String fault) throws IOException {
        exact(request, Set.of("project", "configuration", "expectedRevision"));
        String project = request.getString("project");
        name(project);
        JsonObject config = configuration(request.getObj("configuration"));
        JsonValue expected = request.get("expectedRevision");
        JsonValue observed = projects.hasKey(project) ? projects.getObj(project).get("revision") : JsonNull.instance;
        if (!expected.equals(observed)) throw new JenaSessionEngine.Refusal(409, "Fulltext revision changed; read state before retrying");
        if (projects.hasKey(project) && config.equals(projects.getObj(project).getObj("configuration"))) return state(project);
        JsonObject desired = JSON.parse(JSON.toString(projects));
        JsonObject entry = new JsonObject();
        entry.put("configuration", config);
        entry.put("revision", UUID.randomUUID().toString());
        desired.put(project, entry);
        if (desired.size() > 128) throw new JenaSessionEngine.Refusal(400, "Fulltext project limit exceeded");
        uniqueGraphs(desired);
        Candidate candidate = rebuild(desired);
        boolean published = false;
        try {
            if ("before-publish".equals(fault)) throw new IOException("Injected pre-publication failure");
            JsonObject manifest = new JsonObject();
            manifest.put("version", 1);
            manifest.put("projects", desired);
            Path pending = root.resolve("configuration.pending");
            byte[] bytes = JSON.toString(manifest).getBytes(StandardCharsets.UTF_8);
            try (FileChannel file = FileChannel.open(pending, StandardOpenOption.CREATE,
                    StandardOpenOption.TRUNCATE_EXISTING, StandardOpenOption.WRITE)) {
                ByteBuffer buffer = ByteBuffer.wrap(bytes);
                while (buffer.hasRemaining()) file.write(buffer);
                file.force(true);
            }
            // No non-atomic fallback: an unsupported filesystem must refuse.
            published = true; // A failed rename may still leave an uncertain outcome.
            Files.move(pending, root.resolve("configuration.json"), StandardCopyOption.ATOMIC_MOVE, StandardCopyOption.REPLACE_EXISTING);
            try (FileChannel parent = FileChannel.open(root, StandardOpenOption.READ)) { parent.force(true); }
            if ("after-publish".equals(fault)) throw new IOException("Injected post-publication failure");
        } catch (Exception error) {
            // After publication the result may be durable even if reply/swap
            // failed. Refuse ALL operations until restart rebuilds that state.
            if (published) unavailable = true;
            candidate.index().close();
            removeIndex(candidate.directory());
            throw error;
        }
        JenaTextFixture.Index previous = current;
        Path previousDirectory = directory;
        current = candidate.index();
        directory = candidate.directory();
        projects = desired;
        try {
            if (previous != null) previous.close();
            if (previousDirectory != null) removeIndex(previousDirectory);
        } catch (RuntimeException | IOException error) {
            unavailable = true;
            throw error;
        }
        return state(project);
    }

    static void removeIndex(Path path) throws IOException {
        if (!Files.exists(path)) return;
        try (var entries = Files.walk(path)) {
            for (Path entry : entries.sorted(Comparator.reverseOrder()).toList()) Files.delete(entry);
        }
    }
    @Override public void close() { if (current != null) current.close(); }
}
