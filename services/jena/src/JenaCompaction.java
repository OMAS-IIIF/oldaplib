import java.io.IOException;
import java.nio.file.*;
import java.time.*;
import java.util.*;
import java.util.concurrent.*;
import org.apache.jena.query.ReadWrite;
import org.apache.jena.tdb2.DatabaseMgr;

/** Growth-triggered maintenance over the service-owned TDB dataset.
 *
 * A periodic check also catches bulk-operation growth. Only the transaction owner
 * may compact, with no active session and exclusive maintenance access. Native
 * TDB compaction preserves all RDF (including replay receipts) and switches the
 * generation before retiring its predecessor. Fulltext contents are unchanged.
 * A durable intent marker fences restart after an interrupted/failed compaction;
 * an operator must verify storage/recovery before removing that marker.
 */
final class JenaCompaction implements AutoCloseable {
    record Policy(long checkSeconds, long minSeconds, long growthBytes, double growthRatio, ZoneId zone, LocalTime start, LocalTime end) {
        Policy {
            if (zone == null || start == null || end == null || start.equals(end)
                    || checkSeconds < 60 || minSeconds < checkSeconds || growthBytes < 1024 * 1024
                    || !Double.isFinite(growthRatio) || growthRatio < 1.1)
                throw new IllegalArgumentException("Invalid compaction policy");
        }
    }
    /** Local wall-clock window, start inclusive/end exclusive, including midnight crossing.
     * Zone rules handle daylight saving automatically; elapsed throttling stays UTC-based.
     */
    static boolean inWindow(Policy policy, Instant instant) {
        LocalTime time = instant.atZone(policy.zone()).toLocalTime();
        return policy.start().isBefore(policy.end())
            ? !time.isBefore(policy.start()) && time.isBefore(policy.end())
            : !time.isBefore(policy.start()) || time.isBefore(policy.end());
    }
    private final JenaSessionEngine engine;
    private final Path root, state, intent;
    private final Policy policy;
    private final Clock clock;
    private final ScheduledExecutorService scheduler = Executors.newSingleThreadScheduledExecutor();

    JenaCompaction(JenaSessionEngine engine, Path root, Policy policy, Clock clock) throws IOException {
        this.engine = engine;
        this.root = root;
        this.policy = policy;
        this.clock = clock;
        state = root.resolve("compaction.properties");
        intent = root.resolve("compaction.pending");
        if (Files.exists(intent))
            throw new IllegalStateException("Interrupted compaction requires operator verification");
    }

    /** Schedule checks, not unconditional compactions; no work is done on startup. */
    void start() {
        scheduler.scheduleWithFixedDelay(() -> {
            try {
                String result = check();
                if (!result.equals("not-due") && !result.equals("outside-window")) System.out.println("OLDAP compaction: " + result);
            } catch (Exception failure) {
                // No filesystem paths, configuration values or RDF in log output.
                System.err.println("OLDAP compaction failed; inspect maintenance marker and storage");
            }
        }, policy.checkSeconds(), policy.checkSeconds(), TimeUnit.SECONDS);
    }

    /** Select the active TDB generation without following symlinks. */
    private Path generation() throws IOException {
        try (var paths = Files.list(root)) {
            return paths.filter(p -> p.getFileName().toString().matches("Data-[0-9]+"))
                .peek(p -> { if (Files.isSymbolicLink(p)) throw new IllegalStateException("Symlinked generation"); })
                .filter(Files::isDirectory)
                .max(Comparator.comparingLong(p -> Long.parseLong(p.getFileName().toString().substring(5))))
                .orElseThrow(() -> new IllegalStateException("TDB generation absent"));
        }
    }

    /** Logical bytes are portable and conservatively bound required copy space. */
    static long bytes(Path path) throws IOException {
        try (var files = Files.walk(path)) {
            long total = 0;
            for (Path file : files.toList()) {
                if (Files.isSymbolicLink(file)) throw new IOException("Symlinked storage");
                if (Files.isRegularFile(file)) total = Math.addExact(total, Files.size(file));
            }
            return total;
        }
    }

    /** A single completed baseline is durable across service and machine restarts. */
    private Properties previous() throws IOException {
        Properties result = new Properties();
        if (Files.exists(state)) {
            if (Files.isSymbolicLink(state)) throw new IOException("Symlinked compaction state");
            try (var reader = Files.newBufferedReader(state)) { result.load(reader); }
        }
        return result;
    }

    static boolean due(Policy policy, long size, long baseline, long elapsedSeconds) {
        if (elapsedSeconds < policy.minSeconds()) return false;
        if (baseline == 0) return size >= policy.growthBytes(); // Existing unmaintained stores.
        return size - baseline >= policy.growthBytes() && size >= baseline * policy.growthRatio();
    }

    /** Marshal maintenance onto the same thread as BEGIN/COMMIT and lease expiry. */
    String check() throws Exception {
        return engine.owner.submit(() -> {
            if (!inWindow(policy, clock.instant())) return "outside-window";
            engine.available();
            engine.expire();
            if (engine.session != null) return "writer-active";
            if (!engine.maintenance.writeLock().tryLock()) return "readers-active";
            try {
                Properties prior = previous();
                long now = clock.instant().getEpochSecond();
                long baseline = Long.parseLong(prior.getProperty("bytes", "0"));
                long last = Long.parseLong(prior.getProperty("completed", "0"));
                if (baseline < 0 || last < 0) throw new IOException("Invalid compaction baseline");
                Path old = generation();
                long size = bytes(old);
                if (!due(policy, size, baseline, now - last)) return "not-due";
                var store = Files.getFileStore(root);
                // Keep the same 20% capacity reserve as uploads/backups. A second
                // complete generation must fit before the old one is retired.
                if (store.getUsableSpace() - size < store.getTotalSpace() / 5)
                    return "insufficient-space";
                // Recheck immediately before admission: capacity inspection may take time.
                if (!inWindow(policy, clock.instant())) return "outside-window";
                engine.maintenanceActive = true;
                boolean begun = false;
                try {
                    long before = countQuads();
                    Files.writeString(intent, "generation=" + old.getFileName() + "\nquads=" + before + "\nstarted=" + now + "\n",
                        StandardOpenOption.CREATE_NEW, StandardOpenOption.WRITE);
                    try (var channel = java.nio.channels.FileChannel.open(intent, StandardOpenOption.WRITE)) { channel.force(true); }
                    syncDirectory();
                    begun = true;
                    DatabaseMgr.compact(engine.storage.asDatasetGraph(), true);
                    if (generation().equals(old) || countQuads() != before)
                        throw new IllegalStateException("Compaction verification failed");
                    long after = bytes(generation());
                    Path temporary = root.resolve("compaction.properties.tmp");
                    long completed = clock.instant().getEpochSecond();
                    Files.writeString(temporary, "completed=" + completed + "\nbytes=" + after + "\nquads=" + before + "\n");
                    try (var channel = java.nio.channels.FileChannel.open(temporary, StandardOpenOption.WRITE)) { channel.force(true); }
                    Files.move(temporary, state, StandardCopyOption.ATOMIC_MOVE, StandardCopyOption.REPLACE_EXISTING);
                    syncDirectory();
                    Files.delete(intent);
                    syncDirectory();
                    System.out.println("OLDAP compaction bytes: " + size + " -> " + after);
                    return "completed";
                } catch (Exception failure) {
                    // A failed native operation or final bookkeeping has unknown
                    // outcome. Do not serve writes until an operator checks it.
                    if (begun || Files.exists(intent)) engine.maintenanceFailed = true;
                    throw failure;
                } finally { engine.maintenanceActive = false; }
            } finally { engine.maintenance.writeLock().unlock(); }
        }).get();
    }

    /** Persist marker/rename directory entries as well as file contents. */
    private void syncDirectory() throws IOException {
        try (var channel = java.nio.channels.FileChannel.open(root, StandardOpenOption.READ)) {
            channel.force(true);
        }
    }

    private long countQuads() {
        engine.storage.begin(ReadWrite.READ);
        try {
            long count = 0;
            var quads = engine.storage.asDatasetGraph().find();
            try { while (quads.hasNext()) { quads.next(); count++; } }
            finally { org.apache.jena.atlas.iterator.Iter.close(quads); }
            return count;
        } finally { engine.storage.end(); }
    }

    /** Stop new checks and finish an in-flight check before engine.close(). */
    @Override public void close() throws InterruptedException {
        scheduler.shutdown();
        while (!scheduler.awaitTermination(1, TimeUnit.DAYS)) {
            // Native compaction must finish; never interrupt it to meet a timeout.
        }
    }
}
