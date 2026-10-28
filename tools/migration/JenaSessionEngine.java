import java.io.*;
import java.nio.charset.StandardCharsets;
import java.util.*;
import java.util.concurrent.*;
import org.apache.jena.query.*;
import org.apache.jena.rdf.model.*;
import org.apache.jena.tdb2.TDB2Factory;
import org.apache.jena.update.UpdateAction;

/**
 * Experimental interactive transaction state shared by both HTTP probes.
 * Callers must authenticate the actor before dispatch; this class owns TDB2
 * thread affinity, application/receipt separation, deadline and commit state.
 * It does not implement user login or OLDAP resource permissions.
 */
public class JenaSessionEngine implements AutoCloseable {
    static final String RECEIPTS = "urn:probe:http-commits";
    static final Property OWNER = ResourceFactory.createProperty(RECEIPTS + ":owner");
    final Dataset dataset;
    final Dataset application;
    final ScheduledExecutorService owner = Executors.newSingleThreadScheduledExecutor();
    final long lifetimeMillis;
    final Set<UUID> usedIds = new HashSet<>();
    // Only the owner thread reads/writes these fields or the write transaction.
    UUID session;
    String actor;
    long deadline;

    JenaSessionEngine(String directory, long lifetimeMillis) {
        dataset = TDB2Factory.connectDataset(directory);
        application = DatasetFactory.wrap(new ProtectedApplicationDataset(dataset.asDatasetGraph(), RECEIPTS));
        this.lifetimeMillis = lifetimeMillis;
        owner.scheduleWithFixedDelay(this::expire, 50, 50, TimeUnit.MILLISECONDS);
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
        try (QueryExecution execution = QueryExecutionFactory.create(sparql, dataset)) {
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

    /** Visible state machine: begin, intermediate reads/writes, commit or abort. */
    String execute(String operation, UUID id, String identity, String body) {
        expire();
        if (operation.equals("BEGIN")) {
            if (session != null) throw new Refusal(409, "Writer busy");
            if (usedIds.contains(id)) throw new Refusal(409, "Identifier already used");
            if (usedIds.size() >= 256) throw new Refusal(503, "Probe session budget exhausted");
            // BEGIN never resumes or reuses a committed transaction identifier.
            if (committedOwner(id) != null) throw new Refusal(409, "Identifier already committed");
            dataset.begin(ReadWrite.WRITE);
            usedIds.add(id);
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
            abort();
            throw error;
        }
    }

    /** Dispatch an authenticated request without letting a handler own a write. */
    String dispatch(String operation, UUID id, String identity, String body) throws Exception {
        if (operation.equals("STATUS")) {
            String receiptOwner = committedOwner(id);
            if (receiptOwner != null && !receiptOwner.equals(identity))
                throw new Refusal(403, "Receipt belongs to another actor");
            return receiptOwner == null ? "unknown" : "committed";
        }
        if (operation.equals("READ")) {
            dataset.begin(ReadWrite.READ);
            try { return query(application, body); } finally { dataset.end(); }
        }
        return owner.submit(() -> execute(operation, id, identity, body)).get();
    }

    @Override public void close() throws Exception {
        owner.submit(this::abort).get();
        owner.shutdownNow();
        dataset.close();
    }
}
