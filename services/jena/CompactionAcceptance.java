import java.nio.file.*;
import java.time.*;
import java.util.*;
import org.apache.jena.query.ReadWrite;

/** Real TDB acceptance: writer/read fencing, native generation switch, receipts
 * and domain data preservation, throttling, restart state and interrupted intent.
 * Creates a new disposable root only; no HTTP listener or external service.
 */
public class CompactionAcceptance {
    static void require(boolean condition, String message) {
        if (!condition) throw new AssertionError(message);
    }
    static boolean textHits(JenaSessionEngine engine) throws Exception {
        return engine.dispatch("READ", UUID.randomUUID(), "test", "SELECT ?s WHERE { GRAPH <urn:test:data> { (?s ?score) <http://jena.apache.org/text#query> (<urn:p> \"hello\" 100) } }").contains("urn:s");
    }
    public static void main(String[] args) throws Exception {
        Path root = Path.of(args[0]); Files.createDirectory(root);
        var policy = new JenaCompaction.Policy(60, 60, 1024 * 1024, 2.0, ZoneId.of("Europe/Zurich"), LocalTime.of(1, 0), LocalTime.of(3, 0));
        Clock now = Clock.fixed(Instant.parse("2026-11-07T01:00:00Z"), ZoneOffset.UTC);
        require(!JenaCompaction.due(policy, 10_000_000, 1_000_000, 59), "Minimum interval");
        require(!JenaCompaction.due(policy, 1_500_000, 1_000_000, 60), "Minimum growth");
        require(!JenaCompaction.inWindow(policy, Instant.parse("2026-11-07T11:00:00Z")), "Daytime excluded");
        require(JenaCompaction.inWindow(policy, Instant.parse("2026-11-07T00:00:00Z")), "Inclusive start");
        require(!JenaCompaction.inWindow(policy, Instant.parse("2026-11-07T02:00:00Z")), "Exclusive end");
        require(JenaCompaction.inWindow(policy, Instant.parse("2026-07-07T00:00:00Z")), "Summer timezone");
        require(JenaCompaction.inWindow(policy, Instant.parse("2026-10-25T00:30:00Z"))
            && JenaCompaction.inWindow(policy, Instant.parse("2026-10-25T01:30:00Z")), "Both autumn repeated hours");
        var overnight = new JenaCompaction.Policy(60, 60, 1048576, 2.0, ZoneOffset.UTC, LocalTime.of(23, 0), LocalTime.of(2, 0));
        require(JenaCompaction.inWindow(overnight, Instant.parse("2026-11-07T23:30:00Z"))
            && JenaCompaction.inWindow(overnight, Instant.parse("2026-11-08T01:30:00Z")), "Midnight crossing");
        UUID receipt = UUID.randomUUID();
        try (JenaSessionEngine engine = new JenaSessionEngine(root.toString(), 60000, false, true)) {
            try (var daytime = new JenaCompaction(engine, root, policy,
                    Clock.fixed(Instant.parse("2026-11-07T11:00:00Z"), ZoneOffset.UTC))) {
                require(daytime.check().equals("outside-window"), "No daytime maintenance");
                require(!Files.exists(root.resolve("compaction.pending")), "No daytime intent");
            }
            engine.fulltext("FULLTEXT_APPLY", "{\"project\":\"demo\",\"configuration\":{\"graph\":\"urn:test:data\",\"fields\":{\"title\":[\"urn:p\"]}},\"expectedRevision\":null}", null);
            engine.dispatch("BEGIN", receipt, "test", "");
            engine.dispatch("UPDATE", receipt, "test", "INSERT DATA { GRAPH <urn:test:data> { <urn:s> <urn:p> 'hello' } }");
            engine.dispatch("COMMIT", receipt, "test", "");
            try (JenaCompaction compact = new JenaCompaction(engine, root, policy, now)) {
                UUID active = UUID.randomUUID();
                engine.dispatch("BEGIN", active, "test", "");
                require(compact.check().equals("writer-active"), "Must not interrupt writer");
                engine.dispatch("ABORT", active, "test", "");
                engine.maintenance.readLock().lock();
                try { require(compact.check().equals("readers-active"), "Must not interrupt readers"); }
                finally { engine.maintenance.readLock().unlock(); }
                engine.maintenanceActive = true;
                try {
                    engine.dispatch("READ", UUID.randomUUID(), "test", "ASK {}");
                    throw new AssertionError("Maintenance must refuse new work");
                } catch (JenaSessionEngine.Refusal expected) { require(expected.status == 503, "Retry status"); }
                finally { engine.maintenanceActive = false; }
                require(textHits(engine), "Text before compaction");
                require(compact.check().equals("completed"), "Native compaction completion");
                require(textHits(engine), "Text after compaction");
                require(!Files.exists(root.resolve("Data-0001")), "Retire replaced generation");
                require(Files.isDirectory(root.resolve("Data-0002")), "Switch generation");
                require(engine.dispatch("STATUS", receipt, "test", "").equals("committed"), "Preserve receipt");
                require(engine.dispatch("READ", UUID.randomUUID(), "test", "ASK { GRAPH <urn:test:data> { <urn:s> <urn:p> 'hello' } }").contains("true"), "Preserve domain data");
                require(compact.check().equals("not-due"), "Throttle repeated calls");
                engine.storage.begin(ReadWrite.READ);
                try { require(engine.storage.getNamedModel(JenaSessionEngine.RECEIPTS).size() == 3, "Preserve aborted reservation too"); }
                finally { engine.storage.end(); }
            }
        }
        try (JenaSessionEngine reopened = new JenaSessionEngine(root.toString(), 60000, false, true);
             JenaCompaction compact = new JenaCompaction(reopened, root, policy, now)) {
            require(compact.check().equals("not-due"), "Retain baseline on restart");
            require(textHits(reopened), "Text after restart");
            require(reopened.dispatch("STATUS", receipt, "test", "").equals("committed"), "Durable receipt after restart");
            Files.writeString(root.resolve("compaction.pending"), "interrupted-test\n");
            try {
                new JenaCompaction(reopened, root, policy, now);
                throw new AssertionError("Pending marker must block automatic restart");
            } catch (IllegalStateException expected) { }
        }
        System.out.println("Compaction acceptance passed");
    }
}
