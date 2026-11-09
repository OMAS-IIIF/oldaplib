import java.io.*;
import java.nio.charset.StandardCharsets;
import java.util.*;
import java.util.concurrent.*;
import org.apache.jena.query.*;
import org.apache.jena.rdf.model.*;
import org.apache.jena.tdb2.TDB2Factory;
import org.apache.jena.update.UpdateAction;

/**
 * Interactive transaction state shared by the private service and HTTP probes.
 * Callers must authenticate the actor before dispatch; this class owns TDB2
 * thread affinity, application/receipt separation, deadline and commit state.
 * It does not implement user login or OLDAP resource permissions.
 */
public class JenaSessionEngine implements AutoCloseable {
    static final String RECEIPTS = "urn:probe:http-commits";
    static final Property OWNER = ResourceFactory.createProperty(RECEIPTS + ":owner");
    static final Property RESERVED = ResourceFactory.createProperty(RECEIPTS + ":reservedBy");
    Dataset dataset;
    Dataset application;
    final Dataset storage;
    final JenaManagedText managedText;
    // Readers finish before an index is replaced; owner-thread writes and
    // maintenance are serialized, and active interactive transactions refuse it.
    final java.util.concurrent.locks.ReentrantReadWriteLock maintenance =
        new java.util.concurrent.locks.ReentrantReadWriteLock(true);
    final ScheduledExecutorService owner = Executors.newSingleThreadScheduledExecutor();
    final long lifetimeMillis;
    // Owner writes these fields; request threads may read the volatile maintenance flags.
    volatile boolean maintenanceActive;
    volatile boolean maintenanceFailed;
    UUID session;
    String actor;
    long deadline;
    final java.util.concurrent.atomic.AtomicBoolean closed = new java.util.concurrent.atomic.AtomicBoolean();

    JenaSessionEngine(String directory, long lifetimeMillis) {
        this(directory, lifetimeMillis, false);
    }

    JenaSessionEngine(String directory, long lifetimeMillis, boolean textFixture) {
        this(directory, lifetimeMillis, textFixture, "yes".equals(System.getenv("PROBE_MANAGED_TEXT")));
    }

    /** Explicit service configuration; production never reads probe environment flags. */
    JenaSessionEngine(String directory, long lifetimeMillis, boolean textFixture, boolean managed) {
        if (lifetimeMillis <= 0) throw new IllegalArgumentException("Positive transaction lifetime required");
        storage = TDB2Factory.connectDataset(directory);
        if (managed && textFixture) throw new IllegalArgumentException("Choose managed or fixture text mode");
        if (!managed && java.nio.file.Files.exists(java.nio.file.Path.of(directory, "managed-text", "configuration.json")))
            throw new IllegalArgumentException("Managed text configuration requires managed mode");
        try {
            managedText = managed ? new JenaManagedText(storage, java.nio.file.Path.of(directory, "managed-text")) : null;
        } catch (IOException error) { storage.close(); throw new UncheckedIOException(error); }
        catch (RuntimeException error) { storage.close(); throw error; }
        dataset = managed ? managedText.dataset() : textFixture ? JenaTextFixture.attach(storage, java.nio.file.Path.of(directory, "text-index")) : storage;
        refreshApplication();
        this.lifetimeMillis = lifetimeMillis;
        owner.scheduleWithFixedDelay(this::expire, 50, 50, TimeUnit.MILLISECONDS);
    }

    /** Rebind the protected view only while no request can retain the old index. */
    void refreshApplication() {
        application = DatasetFactory.wrap(new ProtectedApplicationDataset(dataset.asDatasetGraph(), RECEIPTS));
        var index = dataset.getContext().get(org.apache.jena.query.text.TextQuery.textIndex);
        if (index != null) application.getContext().set(org.apache.jena.query.text.TextQuery.textIndex, index);
    }

    void available() {
        if (closed.get()) throw new Refusal(503, "Backend stopping");
        if (maintenanceActive || maintenanceFailed) throw new Refusal(503, "Backend maintenance");
        if (managedText != null && managedText.unavailable)
            throw new Refusal(503, "Fulltext activation outcome requires restart and state inspection");
    }

    /** Private administration boundary; servlet must check the separate admin key. */
    String fulltext(String operation, String body, String fault) throws Exception {
        return owner.submit(() -> {
            expire();
            if (managedText == null) throw new Refusal(503, "Managed fulltext is not enabled");
            // State is immutable during ordinary reads/writes and is inspected on
            // the same owner thread as index replacement. It must coexist with
            // search readers: each search resolves its fields before querying.
            available();
            var request = org.apache.jena.atlas.json.JSON.parse(body);
            if (operation.equals("FULLTEXT_STATE")) {
                JenaManagedText.exact(request, Set.of("project"));
                return managedText.state(request.getString("project"));
            }
            if (session != null) throw new Refusal(409, "Writer active; fulltext administration refused");
            if (!maintenance.writeLock().tryLock()) throw new Refusal(409, "Reader active; retry administration later");
            try {
                String result = managedText.apply(request, fault);
                dataset = managedText.dataset();
                refreshApplication();
                return result;
            } finally { maintenance.writeLock().unlock(); }
        }).get();
    }

    static class Refusal extends RuntimeException {
        final int status;
        Refusal(int status, String reason) { super(reason); this.status = status; }
    }

    /** Cleanup always executes on the same thread that began the transaction. */
    void abort() {
        if (session == null) return;
        try { dataset.abort(); } finally { dataset.end(); session = null; actor = null; }
    }

    void expire() {
        if (session != null && System.nanoTime() >= deadline) abort();
    }

    static String query(Dataset dataset, String sparql) {
        try (QueryExecution execution = QueryExecution.dataset(dataset).query(sparql).timeout(60, TimeUnit.SECONDS).build()) {
            ByteArrayOutputStream result = new ByteArrayOutputStream();
            if (execution.getQuery().isAskType()) ResultSetFormatter.outputAsJSON(result, execution.execAsk());
            else if (execution.getQuery().isSelectType()) ResultSetFormatter.outputAsJSON(result, execution.execSelect());
            else if (execution.getQuery().isConstructType())
                org.apache.jena.riot.RDFDataMgr.write(result, execution.execConstruct(), org.apache.jena.riot.Lang.JSONLD);
            else throw new Refusal(400, "ASK/SELECT/CONSTRUCT only");
            return result.toString(StandardCharsets.UTF_8);
        }
    }

    /** Read committed receipt without joining the owner's pending writes. */
    String committedOwner(UUID id) {
        dataset.begin(ReadWrite.READ);
        try {
            Statement statement = dataset.getNamedModel(RECEIPTS).getProperty(
                ResourceFactory.createResource("urn:uuid:" + id), OWNER);
            return statement == null ? null : statement.getString();
        } finally { dataset.end(); }
    }

    /**
     * Persist an admission tombstone in the already protected metadata graph.
     * Unlike the committed OWNER receipt, this is NOT evidence of user-data commit.
     * Tombstones have no TTL: pruning them would reopen delayed-request replay.
     * Raw storage is intentional; metadata must not enter the fulltext index.
     */
    void reserve(UUID id, String identity) {
        storage.begin(ReadWrite.WRITE);
        try {
            Model metadata = storage.getNamedModel(RECEIPTS);
            Resource resource = ResourceFactory.createResource("urn:uuid:" + id);
            if (metadata.contains(resource, RESERVED) || metadata.contains(resource, OWNER))
                throw new Refusal(409, "Identifier already used");
            metadata.add(resource, RESERVED, identity);
            storage.commit();
        } catch (RuntimeException error) {
            storage.abort();
            throw error;
        } finally { storage.end(); }
    }

    /** Visible state machine: begin, intermediate reads/writes, commit or abort. */
    String execute(String operation, UUID id, String identity, String body) {
        available();
        expire();
        if (operation.equals("BEGIN")) {
            if (session != null) throw new Refusal(409, "Writer busy");
            // Reserve independently before beginning application writes. Even an
            // abort, expiry or crash consumes the ID, so delayed requests cannot
            // accidentally address a later transaction with the same identity.
            reserve(id, identity);
            dataset.begin(ReadWrite.WRITE);
            session = id;
            actor = identity;
            deadline = System.nanoTime() + TimeUnit.MILLISECONDS.toNanos(lifetimeMillis);
            return "active";
        }
        if (!id.equals(session)) {
            if (operation.equals("ABORT")) return "inactive";
            throw new Refusal(409, "No matching active transaction");
        }
        if (!identity.equals(actor)) throw new Refusal(403, "Session belongs to another actor");
        try {
            switch (operation) {
                case "UPDATE": UpdateAction.parseExecute(body, application); return "updated";
                case "QUERY": return query(application, body);
                case "EXPORT_GRAPHS": return JenaProjectTransfer.exportGraphs(application, identity, body);
                case "IMPORT_GRAPHS": return JenaProjectTransfer.importGraphs(application, identity, body);
                case "ABORT": abort(); return "aborted";
                case "COMMIT":
                    // The receipt and application changes become visible atomically.
                    // No replay of callback code or SPARQL is necessary after a lost reply.
                    dataset.getNamedModel(RECEIPTS).add(
                        ResourceFactory.createResource("urn:uuid:" + id), OWNER, identity);
                    dataset.commit();
                    dataset.end();
                    session = null;
                    actor = null;
                    return "committed";
                default: throw new Refusal(400, "Unsupported operation");
            }
        } catch (RuntimeException error) {
            // A failed two-store commit is uncertain. Rebuild before serving
            // another request; do not assume abort can undo a committed store.
            if (operation.equals("COMMIT") && managedText != null) managedText.unavailable = true;
            abort();
            throw error;
        }
    }

    /** Dispatch an authenticated request without letting a handler own a write. */
    String dispatch(String operation, UUID id, String identity, String body) throws Exception {
        available(); // Refuse new work promptly while the owner compacts storage.
        if (Set.of("STATUS", "READ", "FULLTEXT_READ", "READ_GRAPHS").contains(operation)) {
            if (!maintenance.readLock().tryLock()) throw new Refusal(503, "Fulltext rebuild in progress");
            try {
                available();
                if (operation.equals("STATUS")) {
                    String receiptOwner = committedOwner(id);
                    if (receiptOwner != null && !receiptOwner.equals(identity))
                        throw new Refusal(403, "Receipt belongs to another actor");
                    return receiptOwner == null ? "unknown" : "committed";
                }
                String sparql = body;
                if (operation.equals("FULLTEXT_READ")) {
                    if (managedText == null) throw new Refusal(503, "Managed fulltext is not enabled");
                    sparql = managedText.checkedQuery(body);
                }
                dataset.begin(ReadWrite.READ);
                try {
                    return operation.equals("READ_GRAPHS")
                        ? JenaProjectTransfer.exportGraphs(application, identity, body) : query(application, sparql);
                } finally { dataset.end(); }
            } finally { maintenance.readLock().unlock(); }
        }
        return owner.submit(() -> execute(operation, id, identity, body)).get();
    }

    /** Stop owner-thread writes, then wait for retained read/index views to finish. */
    @Override public void close() throws Exception {
        if (!closed.compareAndSet(false, true)) return;
        try { owner.submit(this::abort).get(); }
        finally {
            owner.shutdownNow();
            maintenance.writeLock().lock();
            try {
                if (managedText != null) { managedText.close(); storage.close(); }
                else dataset.close();
            } finally { maintenance.writeLock().unlock(); }
        }
    }
}
