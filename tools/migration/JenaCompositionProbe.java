import com.sun.net.httpserver.HttpExchange;
import com.sun.net.httpserver.HttpServer;
import java.net.InetAddress;
import java.net.InetSocketAddress;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Duration;
import java.util.*;
import java.util.concurrent.*;
import org.apache.jena.query.*;
import org.apache.jena.rdf.model.*;
import org.apache.jena.tdb2.TDB2Factory;

/**
 * Readable, bounded server-command experiment, NOT an OLDAP endpoint.
 * One HTTP request moves a synthetic folder and medium, appends structural
 * history and conditional lifecycle work, and stores an exact replay receipt.
 * The caller supplies only a UUID, expected revision and test failure stage.
 * No raw SPARQL, scripts, arbitrary callbacks or production IRIs are accepted.
 * Input: new dataset directory. Output: PASS lines, throwing on failed checks.
 */
public class JenaCompositionProbe {
    private static final String NS = "urn:jena-composition:";
    private static final String DATA = NS + "data", AUDIT = NS + "audit";
    private static final String OUTBOX = NS + "outbox", RECEIPTS = NS + "receipts";
    private static final List<String> GRAPHS = List.of(DATA, AUDIT, OUTBOX, RECEIPTS);
    private static final Property PARENT = property("parent"), REVISION = property("revision");
    private static final Property CAN_EDIT = property("canEdit"), MOBILE = property("mobileReceipt");
    private static final Property BEFORE = property("before"), AFTER = property("after");
    private static final Property EXPECTED = property("expected"), STATE = property("state");
    private static final Property SOURCE = property("sourceReceipt");
    private static final Resource FOLDER = resource("folder"), MEDIA = resource("media");
    private static final Resource ACTOR = resource("actor"), DESTINATION = resource("destination");
    private static final Resource OLD_PARENT = resource("old-parent"), MOBILE_RECEIPT = resource("upload-receipt");

    private static Property property(String local) { return ResourceFactory.createProperty(NS + local); }
    private static Resource resource(String local) { return ResourceFactory.createResource(NS + local); }
    private static void require(boolean value, String message) {
        if (!value) throw new AssertionError(message);
    }

    /** A fixed move command. Failure injection exists only in this local probe. */
    record Command(UUID operation, long expected, String failAt) {}
    record Result(long revision, boolean replay) {}
    record BeforeState(RDFNode folderParent) {}
    private static class Refusal extends RuntimeException {
        final int status;
        Refusal(int status, String message) { super(message); this.status = status; }
    }

    /** Replace one field; transaction ownership is deliberately NOT hidden here. */
    private static void set(Model model, Resource subject, Property field, RDFNode value) {
        model.removeAll(subject, field, null);
        model.add(subject, field, value);
    }
    private static long revision(Model data, Resource subject) {
        return data.getRequiredProperty(subject, REVISION).getLong();
    }
    private static void failAt(Command command, String stage) {
        if (command.failAt().equals(stage)) throw new Refusal(500, "injected-" + stage);
    }

    /** Validate all read-dependent decisions before changing either resource. */
    private static BeforeState checkPreconditions(Model data, Command command) {
        // Synthetic permission fixture only; real OLDAP ACL/policy guards remain
        // an integration requirement. This does not replace Python authorization.
        if (!data.getRequiredProperty(ACTOR, CAN_EDIT).getBoolean())
            throw new Refusal(403, "permission-denied");
        if (revision(data, FOLDER) != command.expected() || revision(data, MEDIA) != command.expected())
            throw new Refusal(409, "stale-revision");
        return new BeforeState(data.getRequiredProperty(FOLDER, PARENT).getObject());
    }

    /** Both resource helpers join the caller's transaction; neither commits. */
    private static void moveResources(Model data, Command command) {
        set(data, FOLDER, PARENT, DESTINATION);
        set(data, MEDIA, PARENT, FOLDER);
        set(data, FOLDER, REVISION, data.createTypedLiteral(command.expected() + 1));
        set(data, MEDIA, REVISION, data.createTypedLiteral(command.expected() + 1));
    }

    /** Read the newly written folder state inside the same transaction. */
    private static boolean appendStructuralAudit(Dataset dataset, Command command, BeforeState before) {
        Model data = dataset.getNamedModel(DATA), audit = dataset.getNamedModel(AUDIT);
        RDFNode after = data.getRequiredProperty(FOLDER, PARENT).getObject();
        // Match the current structural audit rule: no history entry for an
        // unchanged structure, even if other fields/revisions were updated.
        if (before.folderParent().equals(after)) return false;
        Resource event = resource("audit:" + command.operation());
        audit.add(event, BEFORE, before.folderParent());
        audit.add(event, AFTER, after);
        return true;
    }

    /** Like the existing mobile hook, ordinary non-mobile data creates no work. */
    private static boolean appendLifecycleOutbox(Dataset dataset, Command command) {
        Model data = dataset.getNamedModel(DATA), outbox = dataset.getNamedModel(OUTBOX);
        Statement provenance = data.getProperty(MEDIA, MOBILE);
        if (provenance == null) return false;
        Resource event = resource("outbox:" + command.operation());
        outbox.add(event, SOURCE, provenance.getObject());
        outbox.add(event, AFTER, data.getRequiredProperty(MEDIA, PARENT).getObject());
        outbox.add(event, STATE, "pending");
        return true;
    }

    /** An explicit assertion can abort, unlike a SPARQL WHERE that matched zero rows. */
    private static void verifyAllEffects(Dataset dataset, Command command, boolean audited, boolean mobile) {
        Model data = dataset.getNamedModel(DATA), audit = dataset.getNamedModel(AUDIT);
        Model outbox = dataset.getNamedModel(OUTBOX);
        boolean valid = data.contains(FOLDER, PARENT, DESTINATION)
            && data.contains(MEDIA, PARENT, FOLDER)
            && revision(data, FOLDER) == command.expected() + 1
            && revision(data, MEDIA) == command.expected() + 1
            && (audit.contains(resource("audit:" + command.operation()), AFTER, DESTINATION) == audited)
            && (outbox.contains(resource("outbox:" + command.operation()), AFTER, FOLDER) == mobile);
        if (!valid) throw new Refusal(500, "postcondition-failed");
    }

    /**
     * The only commit boundary. Read this method top to bottom to understand the
     * whole operation. Every helper runs on this thread's active TDB2 transaction.
     * The HTTP handler cannot return success until commit has returned.
     */
    private static Result execute(Dataset dataset, Command command) {
        dataset.begin(ReadWrite.WRITE);
        try {
            Model receipts = dataset.getNamedModel(RECEIPTS);
            Resource receipt = resource("command:" + command.operation());
            if (receipts.containsResource(receipt)) {
                if (receipts.getRequiredProperty(receipt, EXPECTED).getLong() != command.expected())
                    throw new Refusal(409, "operation-id-reused");
                long result = receipts.getRequiredProperty(receipt, REVISION).getLong();
                dataset.abort(); // Replay reads the old result and writes nothing.
                return new Result(result, true);
            }
            BeforeState before = checkPreconditions(dataset.getNamedModel(DATA), command);
            moveResources(dataset.getNamedModel(DATA), command);
            failAt(command, "resources");
            boolean audited = appendStructuralAudit(dataset, command, before);
            failAt(command, "audit");
            boolean mobile = appendLifecycleOutbox(dataset, command);
            failAt(command, "outbox");
            // Test a genuine final assertion failure, not just a thrown hook error.
            if (command.failAt().equals("postcondition"))
                dataset.getNamedModel(AUDIT).removeAll(resource("audit:" + command.operation()), AFTER, null);
            verifyAllEffects(dataset, command, audited, mobile);
            receipts.addLiteral(receipt, EXPECTED, command.expected());
            receipts.addLiteral(receipt, REVISION, command.expected() + 1);
            failAt(command, "receipt");
            dataset.commit();
            return new Result(command.expected() + 1, false);
        } catch (RuntimeException error) {
            dataset.abort();
            throw error;
        } finally { dataset.end(); }
    }

    /** Fixed, small probe wire format: UUID + revision + failure stage, one per line. */
    private static void handle(Dataset dataset, HttpExchange exchange) throws java.io.IOException {
        int status = 200;
        String body;
        try {
            if (!exchange.getRequestMethod().equals("POST")) throw new Refusal(405, "POST-required");
            byte[] bytes = exchange.getRequestBody().readNBytes(1025);
            if (bytes.length > 1024) throw new Refusal(400, "request-too-large");
            String[] fields = new String(bytes, StandardCharsets.UTF_8).split("\n", -1);
            if (fields.length != 3) throw new Refusal(400, "invalid-command");
            Command command = new Command(UUID.fromString(fields[0]), Long.parseLong(fields[1]), fields[2]);
            if (command.expected() < 0 || command.expected() == Long.MAX_VALUE
                    || !Set.of("", "resources", "audit", "outbox", "receipt", "postcondition").contains(command.failAt()))
                throw new Refusal(400, "invalid-command");
            Result result = execute(dataset, command);
            body = (result.replay() ? "replayed:" : "committed:") + result.revision();
        } catch (Refusal error) {
            status = error.status; body = error.getMessage();
        } catch (IllegalArgumentException error) {
            status = 400; body = "invalid-command";
        } catch (Exception error) {
            status = 500; body = "command-failed";
            error.printStackTrace(System.err);
        }
        byte[] response = body.getBytes(StandardCharsets.UTF_8);
        exchange.getResponseHeaders().set("Content-Type", "text/plain; charset=utf-8");
        exchange.sendResponseHeaders(status, response.length);
        try (var stream = exchange.getResponseBody()) { stream.write(response); }
        finally { exchange.close(); }
    }

    /** Snapshot all graphs, so a rollback check also detects stray audit/outbox/receipt triples. */
    private static Map<String, Model> snapshot(Dataset dataset) {
        dataset.begin(ReadWrite.READ);
        try {
            Map<String, Model> result = new HashMap<>();
            for (String graph : GRAPHS)
                result.put(graph, ModelFactory.createDefaultModel().add(dataset.getNamedModel(graph)));
            return result;
        } finally { dataset.end(); }
    }
    private static void same(Map<String, Model> expected, Dataset dataset) {
        Map<String, Model> actual = snapshot(dataset);
        for (String graph : GRAPHS)
            require(expected.get(graph).isIsomorphicWith(actual.get(graph)), "Unexpected effects in " + graph);
    }
    private static void pass(String name) { System.out.println("PASS " + name); }
    private static HttpResponse<String> send(HttpClient client, URI endpoint, Command command) throws Exception {
        return client.send(HttpRequest.newBuilder(endpoint).timeout(Duration.ofSeconds(15))
            .POST(HttpRequest.BodyPublishers.ofString(command.operation() + "\n" + command.expected() + "\n" + command.failAt()))
            .build(), HttpResponse.BodyHandlers.ofString());
    }

    public static void main(String[] args) throws Exception {
        if (args.length != 1 || Files.exists(Path.of(args[0])))
            throw new IllegalArgumentException("Supply one new dataset directory");
        Dataset dataset = TDB2Factory.connectDataset(args[0]);
        HttpServer server = null;
        ExecutorService handlers = Executors.newFixedThreadPool(3), competitors = Executors.newFixedThreadPool(2);
        Map<String, Model> committed;
        try (HttpClient client = HttpClient.newHttpClient()) {
            dataset.begin(ReadWrite.WRITE);
            try {
                Model data = dataset.getNamedModel(DATA);
                data.add(FOLDER, PARENT, OLD_PARENT).add(MEDIA, PARENT, OLD_PARENT);
                data.addLiteral(FOLDER, REVISION, 1L).addLiteral(MEDIA, REVISION, 1L);
                data.addLiteral(ACTOR, CAN_EDIT, true).add(MEDIA, MOBILE, MOBILE_RECEIPT);
                dataset.commit();
            } finally { dataset.end(); }
            server = HttpServer.create(new InetSocketAddress(InetAddress.getLoopbackAddress(), 0), 0);
            server.createContext("/move-pair", exchange -> handle(dataset, exchange));
            server.setExecutor(handlers);
            server.start();
            URI endpoint = new URI("http", null, server.getAddress().getAddress().getHostAddress(),
                server.getAddress().getPort(), "/move-pair", null, null);
            dataset.begin(ReadWrite.WRITE);
            try { set(dataset.getNamedModel(DATA), ACTOR, CAN_EDIT, ResourceFactory.createTypedLiteral(false)); dataset.commit(); }
            finally { dataset.end(); }
            Map<String, Model> denied = snapshot(dataset);
            require(send(client, endpoint, new Command(UUID.randomUUID(), 1, "")).statusCode() == 403, "Permission guard bypassed");
            same(denied, dataset);
            pass("permission guard has no resource/audit/outbox/receipt effects");
            dataset.begin(ReadWrite.WRITE);
            try { set(dataset.getNamedModel(DATA), ACTOR, CAN_EDIT, ResourceFactory.createTypedLiteral(true)); dataset.commit(); }
            finally { dataset.end(); }
            Map<String, Model> original = snapshot(dataset);
            require(send(client, endpoint, new Command(UUID.randomUUID(), 0, "")).statusCode() == 409, "Stale request accepted");
            same(original, dataset);
            pass("stale guard has no resource/audit/outbox/receipt effects");
            for (String stage : List.of("resources", "audit", "outbox", "receipt", "postcondition")) {
                require(send(client, endpoint, new Command(UUID.randomUUID(), 1, stage)).statusCode() == 500, "Injection failed");
                same(original, dataset);
                pass("full rollback at " + stage);
            }
            Command first = new Command(UUID.randomUUID(), 1, "");
            require(send(client, endpoint, first).body().equals("committed:2"), "Commit failed");
            committed = snapshot(dataset);
            require(committed.get(AUDIT).contains(resource("audit:" + first.operation()), BEFORE, OLD_PARENT), "Old state missing");
            require(committed.get(AUDIT).contains(resource("audit:" + first.operation()), AFTER, DESTINATION), "New state missing");
            require(committed.get(OUTBOX).contains(resource("outbox:" + first.operation()), AFTER, FOLDER), "Outbox missing");
            pass("one HTTP command commits both resources, before/after audit, outbox and receipt");
            require(send(client, endpoint, first).body().equals("replayed:2"), "Replay failed");
            same(committed, dataset);
            require(send(client, endpoint, new Command(first.operation(), 2, "")).statusCode() == 409, "ID collision accepted");
            same(committed, dataset);
            pass("exact replay is unchanged; changed ID payload is rejected");
            CountDownLatch start = new CountDownLatch(1);
            List<Future<Integer>> requests = new ArrayList<>();
            for (int i = 0; i < 2; i++) requests.add(competitors.submit(() -> {
                start.await(); return send(client, endpoint, new Command(UUID.randomUUID(), 2, "")).statusCode();
            }));
            start.countDown();
            List<Integer> statuses = new ArrayList<>();
            for (Future<Integer> request : requests) statuses.add(request.get(20, TimeUnit.SECONDS));
            Collections.sort(statuses);
            require(statuses.equals(List.of(200, 409)), "Concurrent commands both won/lost");
            require(send(client, endpoint, first).body().equals("replayed:2"), "Historical result changed");
            pass("concurrent commands have one winner; old replay returns its original revision");
            dataset.begin(ReadWrite.WRITE);
            try { dataset.getNamedModel(DATA).removeAll(MEDIA, MOBILE, null); dataset.commit(); }
            finally { dataset.end(); }
            Command legacy = new Command(UUID.randomUUID(), 3, "");
            require(send(client, endpoint, legacy).statusCode() == 200, "Non-mobile command failed");
            committed = snapshot(dataset);
            require(!committed.get(OUTBOX).containsResource(resource("outbox:" + legacy.operation())), "Legacy media emitted work");
            pass("non-mobile resource does not emit lifecycle work");
            require(!committed.get(AUDIT).containsResource(resource("audit:" + legacy.operation())), "Unchanged structure emitted audit");
            pass("unchanged structure does not emit structural history");
        } finally {
            if (server != null) server.stop(0);
            handlers.shutdownNow(); competitors.shutdownNow(); dataset.close();
        }
        Dataset reopened = TDB2Factory.connectDataset(args[0]);
        try { same(committed, reopened); }
        finally { reopened.close(); }
        pass("all committed graph contents survive close/reopen");
    }
}
