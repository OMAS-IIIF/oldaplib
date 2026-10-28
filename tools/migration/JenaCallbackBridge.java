import java.io.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.util.Base64;
import java.util.concurrent.*;
import org.apache.jena.query.*;
import org.apache.jena.tdb2.TDB2Factory;
import org.apache.jena.update.UpdateAction;

/**
 * Test-only private-pipe bridge for existing Python transaction callbacks.
 * One process owns one dataset and one client. All write transaction calls run
 * on this same thread, as required by TDB2; a separate reader observes isolation.
 * No listening socket, authentication API, sessions, or deployment interface.
 * Wire: OP TAB base64(payload); response OK/ERROR TAB base64(result).
 */
public class JenaCallbackBridge {
    private static String query(Dataset dataset, String sparql) {
        try (QueryExecution execution = QueryExecutionFactory.create(sparql, dataset)) {
            ByteArrayOutputStream output = new ByteArrayOutputStream();
            Query parsed = execution.getQuery();
            if (parsed.isAskType()) ResultSetFormatter.outputAsJSON(output, execution.execAsk());
            else if (parsed.isSelectType()) ResultSetFormatter.outputAsJSON(output, execution.execSelect());
            else throw new IllegalArgumentException("Only ASK/SELECT are supported by this probe");
            return output.toString(StandardCharsets.UTF_8);
        }
    }

    private static void reply(String status, String value) {
        System.out.println(status + "\t" + Base64.getEncoder().encodeToString(value.getBytes(StandardCharsets.UTF_8)));
        System.out.flush();
    }

    public static void main(String[] args) throws Exception {
        if (args.length != 2 || !java.util.Set.of("new", "reopen").contains(args[1]))
            throw new IllegalArgumentException("Expected dataset directory and new/reopen");
        if (Files.exists(Path.of(args[0])) != args[1].equals("reopen"))
            throw new IllegalArgumentException("Unexpected dataset existence");
        Dataset dataset = TDB2Factory.connectDataset(args[0]);
        ExecutorService reader = Executors.newSingleThreadExecutor();
        BufferedReader input = new BufferedReader(new InputStreamReader(System.in, StandardCharsets.UTF_8));
        try {
            String line;
            while ((line = input.readLine()) != null) {
                try {
                    String[] parts = line.split("\t", -1);
                    if (parts.length != 2) throw new IllegalArgumentException("Invalid bridge request");
                    String body = new String(Base64.getDecoder().decode(parts[1]), StandardCharsets.UTF_8);
                    String result = "";
                    switch (parts[0]) {
                        case "BEGIN" -> {
                            if (dataset.isInTransaction()) throw new IllegalStateException("Already active");
                            dataset.begin(ReadWrite.WRITE);
                        }
                        case "UPDATE", "QUERY", "COMMIT" -> {
                            if (!dataset.isInTransaction()) throw new IllegalStateException("No active transaction");
                            if (parts[0].equals("UPDATE")) UpdateAction.parseExecute(body, dataset);
                            else if (parts[0].equals("QUERY")) result = query(dataset, body);
                            else {
                                dataset.commit();
                                dataset.end();
                            }
                        }
                        case "ABORT" -> {
                            if (dataset.isInTransaction()) { dataset.abort(); dataset.end(); }
                        }
                        case "READ" -> {
                            // A different thread takes a committed snapshot even
                            // while the writer has staged resource/outbox changes.
                            result = reader.submit(() -> {
                                dataset.begin(ReadWrite.READ);
                                try { return query(dataset, body); }
                                finally { dataset.end(); }
                            }).get(15, TimeUnit.SECONDS);
                        }
                        default -> throw new IllegalArgumentException("Unsupported bridge operation");
                    }
                    reply("OK", result);
                } catch (Exception error) {
                    // A transport/query error must not leave a usable half-failed
                    // transaction. Python's owner may still issue an idempotent abort.
                    if (dataset.isInTransaction()) { dataset.abort(); dataset.end(); }
                    reply("ERROR", error.getClass().getSimpleName() + ": " + error.getMessage());
                }
            }
        } finally {
            // EOF means the client disappeared, not an implicit commit.
            if (dataset.isInTransaction()) { dataset.abort(); dataset.end(); }
            reader.shutdownNow();
            dataset.close();
        }
    }
}
