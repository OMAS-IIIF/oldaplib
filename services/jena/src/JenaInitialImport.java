import java.nio.file.*;
import java.nio.file.attribute.PosixFilePermissions;
import java.security.MessageDigest;
import java.util.*;
import org.apache.jena.atlas.json.*;
import org.apache.jena.query.*;
import org.apache.jena.riot.*;
import org.apache.jena.riot.tokens.*;
import org.apache.jena.tdb2.TDB2Factory;

/** Offline initial import of a reviewed RDF 1.2 snapshot, including real accounts.
 *
 * Arguments: converted TriG file, expected SHA-256, NEW absolute dataset path.
 * No inference, model replacement, grant repair or network access occurs here.
 * Conversion and domain migrations must precede this step. All graphs, including
 * operational records, are retained; worker reconciliation is a separate gate.
 * The service marker is published only after closing/reopening and verifying the
 * complete RDF dataset. A failed target remains unmarked for inspection and must
 * never be retried in place. The private report contains counts/hashes, not RDF.
 */
public final class JenaInitialImport {
    static final int MAX_BYTES = 64 * 1024 * 1024;

    /** TDB2 drops insignificant fractional-second zeros for inline timestamps.
     * Compare that spelling equivalence only; do not relax datatype, timezone,
     * precision, grant, graph or other literal equality. Keep source bytes intact.
     */
    static Dataset timestampComparable(Dataset input) {
        Dataset result = DatasetFactory.create();
        input.asDatasetGraph().find().forEachRemaining(q -> {
            var object = q.getObject();
            if (object.isLiteral() && object.getLiteralDatatypeURI().equals(
                    "http://www.w3.org/2001/XMLSchema#dateTimeStamp")) {
                String spelling = object.getLiteralLexicalForm()
                    .replaceFirst("(\\.\\d*?[1-9])0+(?=Z$|[+-]\\d{2}:\\d{2}$)", "$1")
                    .replaceFirst("\\.0+(?=Z$|[+-]\\d{2}:\\d{2}$)", "");
                object = org.apache.jena.graph.NodeFactory.createLiteralDT(spelling, object.getLiteralDatatype());
            }
            result.asDatasetGraph().add(org.apache.jena.sparql.core.Quad.create(
                q.getGraph(), q.getSubject(), q.getPredicate(), object));
        });
        return result;
    }

    public static void main(String[] args) throws Exception {
        if (args.length != 3 || !args[1].matches("[a-f0-9]{64}"))
            throw new IllegalArgumentException("Expected converted.trig SHA256 NEW-absolute-dataset");
        Path input = Path.of(args[0]), target = Path.of(args[2]);
        if (!target.isAbsolute() || Files.exists(target, LinkOption.NOFOLLOW_LINKS))
            throw new IllegalArgumentException("Target must be a new absolute directory");
        byte[] bytes;
        try (var stream = Files.newInputStream(input)) { bytes = stream.readNBytes(MAX_BYTES + 1); }
        if (bytes.length > MAX_BYTES) throw new IllegalArgumentException("Converted snapshot exceeds 64 MiB");
        String digest = HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(bytes));
        if (!digest.equals(args[1])) throw new IllegalArgumentException("Reviewed snapshot checksum mismatch");
        String text = java.nio.charset.StandardCharsets.UTF_8.newDecoder()
            .decode(java.nio.ByteBuffer.wrap(bytes)).toString();
        if (text.lines().anyMatch(line -> line.stripLeading().startsWith("#>>")))
            throw new IllegalArgumentException("Account side-channel records require separate migration");
        // Jena also accepts legacy RDF-star. Do not silently bypass conversion.
        Tokenizer tokens = TokenizerText.fromString(text);
        try {
            while (tokens.hasNext()) {
                TokenType type = tokens.next().getType();
                if (type == TokenType.LT2 || type == TokenType.GT2)
                    throw new IllegalArgumentException("Legacy quoted triples require conversion first");
            }
        } finally { tokens.close(); }
        Dataset source = DatasetFactory.create();
        try {
            RDFParser.fromString(text, Lang.TRIG).checking(true).parse(source);
            if (source.containsNamedModel(JenaSessionEngine.RECEIPTS))
                throw new IllegalArgumentException("Source contains reserved backend receipts");
            Files.createDirectory(target, PosixFilePermissions.asFileAttribute(
                PosixFilePermissions.fromString("rwx------")));
            Dataset destination = TDB2Factory.connectDataset(target.toString());
            try {
                destination.begin(ReadWrite.WRITE);
                try {
                    source.asDatasetGraph().find().forEachRemaining(destination.asDatasetGraph()::add);
                    destination.commit();
                } finally { destination.end(); }
            } finally { destination.close(); }
            // Reopen storage: verification must cover persisted RDF, not an in-memory view.
            destination = TDB2Factory.connectDataset(target.toString());
            try {
                destination.begin(ReadWrite.READ);
                try {
                    Dataset expected = timestampComparable(source), actual = timestampComparable(destination);
                    try {
                        if (!ConvertLegacyRdfStar.sameDataset(expected, actual))
                            throw new IllegalStateException("Persisted dataset differs from reviewed snapshot");
                    } finally { expected.close(); actual.close(); }
                } finally { destination.end(); }
            } finally { destination.close(); }
            JsonObject counts = new JsonObject();
            Map<String, Long> graphs = new TreeMap<>();
            source.asDatasetGraph().find().forEachRemaining(q ->
                graphs.merge(q.isDefaultGraph() ? "@default" : q.getGraph().toString(), 1L, Long::sum));
            graphs.forEach((graph, count) -> counts.put(graph, count.longValue()));
            JsonObject report = new JsonObject();
            report.put("sourceSha256", digest);
            report.put("persistedDatasetVerified", true);
            report.put("comparison", "RDF dataset isomorphism; insignificant dateTimeStamp fractional zeros ignored");
            report.put("graphs", counts);
            report.put("scope", "Initial RDF import only; no model migration, fulltext configuration or worker activation");
            Files.writeString(target.resolve("initial-import.json"), JSON.toString(report) + "\n", StandardOpenOption.CREATE_NEW);
            Files.writeString(target.resolve("oldap-service-format"), JenaService.FORMAT, StandardOpenOption.CREATE_NEW);
            System.out.println("Initial RDF import verified; fulltext and application acceptance remain required.");
        } finally { source.close(); }
    }
}
