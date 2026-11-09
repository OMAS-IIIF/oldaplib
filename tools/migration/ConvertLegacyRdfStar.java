import java.io.*;
import java.nio.*;
import java.nio.charset.*;
import java.nio.file.*;
import java.nio.file.attribute.PosixFilePermissions;
import java.security.MessageDigest;
import java.util.*;
import java.util.zip.GZIPInputStream;
import org.apache.jena.atlas.json.*;
import org.apache.jena.graph.*;
import org.apache.jena.query.*;
import org.apache.jena.riot.*;
import org.apache.jena.riot.out.NodeFmtLib;
import org.apache.jena.riot.tokens.*;
import org.apache.jena.sparql.core.Quad;
import org.apache.jena.sparql.graph.GraphFactory;

/** Offline, bounded OLDAP RDF-star conversion. Never connects to a database.
 * Input: plain/gzip TriG with flat quoted OLDAP membership subjects.
 * Output: a new private directory containing converted.trig and report.json.
 * Native parsing preserves RDF syntax; strings/comments are never rewritten.
 * Unsupported constructs fail before output is created. No inference is used.
 */
public class ConvertLegacyRdfStar {
    static final String BASE = "http://oldap.org/base#";
    static final Node REIFIES = NodeFactory.createURI("http://www.w3.org/1999/02/22-rdf-syntax-ns#reifies");
    static final String RELATIVE_BASE = "https://invalid.oldap.example/relative-input/";
    static final int MAX_INPUT = 16 * 1024 * 1024;
    static final Map<String, String> PERMISSIONS = Map.of(
        BASE + "inProject", BASE + "hasAdminPermission",
        BASE + "hasRole", BASE + "hasDefaultDataPermission",
        BASE + "attachedToRole", BASE + "hasDataPermission");
    record Key(Node graph, Node reifier) {}
    record Converted(Dataset dataset, JsonObject report) implements AutoCloseable {
        public void close() { dataset.close(); }
    }

    static String hash(byte[] bytes) throws Exception {
        return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(bytes));
    }

    /** Reject mixed/new syntax, nested quotations and serialized user comments. */
    static void checkSyntax(String source) {
        // These comments are an old tools side-channel, not RDF. Silently
        // discarding them would lose the user-account part of a project dump.
        if (source.lines().anyMatch(line -> line.stripLeading().startsWith("#>>")))
            throw new IllegalArgumentException("Serialized user records require separate account migration");
        Tokenizer tokens = TokenizerText.fromString(source);
        int depth = 0;
        try {
            while (tokens.hasNext()) {
                TokenType type = tokens.next().getType();
                if (Set.of(TokenType.L_TRIPLE, TokenType.R_TRIPLE, TokenType.L_ANN,
                           TokenType.R_ANN, TokenType.TILDE).contains(type))
                    throw new IllegalArgumentException("Expected flat legacy RDF-star, not mixed RDF 1.2/annotation syntax");
                if (type == TokenType.LT2 && ++depth > 1)
                    throw new IllegalArgumentException("Nested quoted triples require manual migration");
                if (type == TokenType.GT2) depth--;
            }
            if (depth != 0) throw new IllegalArgumentException("Unbalanced quoted triple");
        } finally { tokens.close(); }
    }

    static void checkAbsolute(Node node) {
        // RDF4J non-star exports encode quoted triples as opaque URIs. Treating
        // those as ordinary resources would silently disconnect their grants.
        if (node.isURI() && node.getURI().startsWith("urn:rdf4j:triple:"))
            throw new IllegalArgumentException("Encoded RDF4J triple URI: export using an RDF-star format");
        if (node.isURI() && node.getURI().startsWith(RELATIVE_BASE))
            throw new IllegalArgumentException("Relative IRIs require an explicit source base");
        if (node.isLiteral() && node.getLiteralDatatypeURI() != null && node.getLiteralDatatypeURI().startsWith(RELATIVE_BASE))
            throw new IllegalArgumentException("Relative datatype requires an explicit source base");
        if (node.isTripleTerm()) {
            Triple triple = node.getTriple();
            checkAbsolute(triple.getSubject()); checkAbsolute(triple.getPredicate()); checkAbsolute(triple.getObject());
        }
    }

    /** Normalize only supported OLDAP annotation subjects, leaving other RDF intact. */
    static Converted convert(String source) throws Exception {
        checkSyntax(source);
        Dataset parsed = DatasetFactory.create(), result = DatasetFactory.create();
        try {
            RDFParser.fromString(source, Lang.TRIG).base(RELATIVE_BASE).checking(true).parse(parsed);
            List<Quad> quads = new ArrayList<>();
            parsed.asDatasetGraph().find().forEachRemaining(quads::add);
            Map<Key, Node> replacements = new HashMap<>();
            Map<Key, Triple> memberships = new HashMap<>();
            Set<Node> stable = new HashSet<>(), orphaned = new HashSet<>();
            for (Quad quad : quads) {
                for (Node n : List.of(quad.getGraph(), quad.getSubject(), quad.getPredicate(), quad.getObject())) checkAbsolute(n);
                if (!quad.getPredicate().equals(REIFIES)) continue;
                if (!quad.getSubject().isBlank() || !quad.getObject().isTripleTerm() || !quad.getGraph().isURI() || quad.isDefaultGraph())
                    throw new IllegalArgumentException("Unsupported explicit reification or annotation graph");
                Triple triple = quad.getObject().getTriple();
                if (!triple.getSubject().isURI() || !triple.getObject().isURI()
                    || !PERMISSIONS.containsKey(triple.getPredicate().getURI()))
                    throw new IllegalArgumentException("Only URI-based OLDAP membership annotations are supported");
                String identity = "oldap-legacy-membership-v1\n" + NodeFmtLib.strNT(quad.getGraph()) + "\n"
                    + NodeFmtLib.strNT(triple.getSubject()) + "\n" + NodeFmtLib.strNT(triple.getPredicate()) + "\n" + NodeFmtLib.strNT(triple.getObject());
                Node reifier = NodeFactory.createURI("urn:oldap:migrated-grant:" + hash(identity.getBytes(StandardCharsets.UTF_8)));
                Key key = new Key(quad.getGraph(), quad.getSubject());
                if (memberships.putIfAbsent(key, triple) != null)
                    throw new IllegalArgumentException("Ambiguous input reifier");
                replacements.put(key, reifier);
                stable.add(reifier);
                if (!parsed.asDatasetGraph().contains(quad.getGraph(), triple.getSubject(), triple.getPredicate(), triple.getObject()))
                    orphaned.add(reifier);
            }
            Set<Node> generated = new HashSet<>();
            replacements.keySet().forEach(key -> generated.add(key.reifier()));
            long ordinary = 0;
            for (Quad quad : quads) {
                if (stable.contains(quad.getSubject()) || stable.contains(quad.getObject()) || stable.contains(quad.getGraph()) || stable.contains(quad.getPredicate()))
                    throw new IllegalArgumentException("Generated reifier IRI collides with input data");
                if (generated.contains(quad.getObject()) || generated.contains(quad.getGraph()))
                    throw new IllegalArgumentException("Quoted triples as objects/graph names require manual migration");
                Key key = new Key(quad.getGraph(), quad.getSubject());
                Node subject = replacements.get(key);
                if (subject != null) {
                    if (PERMISSIONS.containsValue(quad.getPredicate().getURI())
                        && !PERMISSIONS.get(memberships.get(key).getPredicate().getURI()).equals(quad.getPredicate().getURI()))
                        throw new IllegalArgumentException("Permission predicate does not match its membership type");
                    result.asDatasetGraph().add(Quad.create(quad.getGraph(), subject, quad.getPredicate(), quad.getObject()));
                } else {
                    if (quad.getSubject().isTripleTerm() || quad.getObject().isTripleTerm())
                        throw new IllegalArgumentException("Unsupported triple term outside an annotation");
                    result.asDatasetGraph().add(quad);
                    ordinary++;
                }
            }
            JsonObject report = new JsonObject();
            report.put("formatVersion", 1);
            report.put("sourceTextSha256", hash(source.getBytes(StandardCharsets.UTF_8)));
            report.put("ordinaryQuadsPreserved", ordinary);
            report.put("parsedAnnotationOccurrences", replacements.size());
            report.put("membershipReifiers", stable.size());
            report.put("orphanedMembershipReifiers", orphaned.size());
            report.put("assertedMembershipsAdded", 0);
            report.put("mode", "offline-review-only");
            return new Converted(result, report);
        } catch (Exception error) { result.close(); throw error; }
        finally { parsed.close(); }
    }

    /** Read a local file only, enforce decompressed bound and reject invalid UTF-8. */
    static String read(Path path) throws Exception {
        try (InputStream file = Files.newInputStream(path);
             InputStream in = path.toString().endsWith(".gz") ? new GZIPInputStream(file) : file) {
            byte[] bytes = in.readNBytes(MAX_INPUT + 1);
            if (bytes.length > MAX_INPUT) throw new IllegalArgumentException("Input exceeds 16 MiB decompressed limit");
            return StandardCharsets.UTF_8.newDecoder().onMalformedInput(CodingErrorAction.REPORT).decode(ByteBuffer.wrap(bytes)).toString();
        }
    }

    /** Represent quads as rows in one verification graph, using four fixed columns.
     * Jena's graph matcher refines blank-node neighborhoods; the generic dataset
     * tuple matcher can backtrack exponentially on repetitive real SHACL shapes.
     * One shared graph preserves blank-node identity across source graphs (and
     * blank graph names). Row nodes are fresh; original RDF is never modified.
     */
    static Graph verificationGraph(Dataset dataset) {
        Graph graph = GraphFactory.createDefaultGraph();
        Node[] columns = {NodeFactory.createURI("urn:oldap:verify:graph"),
            NodeFactory.createURI("urn:oldap:verify:subject"),
            NodeFactory.createURI("urn:oldap:verify:predicate"),
            NodeFactory.createURI("urn:oldap:verify:object")};
        dataset.asDatasetGraph().find().forEachRemaining(quad -> {
            Node row = NodeFactory.createBlankNode();
            Node[] values = {quad.getGraph(), quad.getSubject(), quad.getPredicate(), quad.getObject()};
            for (int i = 0; i < columns.length; i++)
                graph.add(Triple.create(row, columns[i], values[i]));
        });
        return graph;
    }

    /** Compare dataset meaning with one global blank-node mapping. */
    static boolean sameDataset(Dataset expected, Dataset actual) {
        Graph left = verificationGraph(expected), right = verificationGraph(actual);
        try { return left.isIsomorphicWith(right); }
        finally { left.close(); right.close(); }
    }

    public static void main(String[] args) throws Exception {
        if (args.length != 2) throw new IllegalArgumentException("Expected local input.trig[.gz] and new output directory");
        Path destination = Path.of(args[1]);
        if (Files.exists(destination)) throw new IllegalArgumentException("Output directory must not exist");
        try (Converted converted = convert(read(Path.of(args[0])))) {
            ByteArrayOutputStream bytes = new ByteArrayOutputStream();
            RDFDataMgr.write(bytes, converted.dataset(), Lang.TRIG);
            Dataset roundtrip = DatasetFactory.create();
            try {
                RDFParser.source(new ByteArrayInputStream(bytes.toByteArray())).lang(Lang.TRIG).parse(roundtrip);
                if (!sameDataset(converted.dataset(), roundtrip))
                    throw new IllegalStateException("Serialized RDF 1.2 failed dataset round-trip verification");
            } finally { roundtrip.close(); }
            converted.report().put("outputSha256", hash(bytes.toByteArray()));
            converted.report().put("roundTripVerified", true);
            Files.createDirectory(destination, PosixFilePermissions.asFileAttribute(PosixFilePermissions.fromString("rwx------")));
            try {
                Files.write(destination.resolve("converted.trig"), bytes.toByteArray(), StandardOpenOption.CREATE_NEW);
                Files.writeString(destination.resolve("report.json"), JSON.toString(converted.report()) + "\n", StandardOpenOption.CREATE_NEW);
            } catch (Exception error) {
                Files.deleteIfExists(destination.resolve("report.json"));
                Files.deleteIfExists(destination.resolve("converted.trig"));
                Files.delete(destination);
                throw error;
            }
            System.out.println("Converted and verified locally; no database changes. See report.json.");
        }
    }
}
