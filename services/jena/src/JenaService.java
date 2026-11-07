import java.io.IOException;
import java.net.URI;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.nio.file.attribute.PosixFilePermission;
import java.util.*;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.atomic.AtomicBoolean;
import org.apache.jena.fuseki.main.FusekiServer;
import jakarta.servlet.http.*;

/**
 * Persistent private OLDAP backend. Owns one TDB2 dataset and a loopback listener.
 * Configuration is explicit; no probe environment, seed files or fault headers
 * can enable test behavior. The API remains responsible for resource permissions.
 * SIGTERM stops admission, drains HTTP work, aborts the active write and closes
 * indexes/storage. Closing stdin does not affect this service.
 */
public final class JenaService {
    static final String FORMAT = "oldap-jena-service-1\n";
    private static final Set<String> KEYS = Set.of("dataset", "port", "transactionLifetimeMillis",
        "identityUrl", "identitySecret", "serviceSecret", "bootstrapSecret", "fulltextSecret");

    /** Load a private, strict properties file. Secrets are never echoed in errors. */
    static Properties settings(Path path) throws IOException {
        if (Files.isSymbolicLink(path) || !Files.isRegularFile(path))
            throw new IllegalArgumentException("Configuration must be a regular non-symlink file");
        Set<PosixFilePermission> permissions = Files.getPosixFilePermissions(path);
        if (permissions.stream().anyMatch(p -> p.name().startsWith("GROUP_") || p.name().startsWith("OTHERS_")))
            throw new IllegalArgumentException("Configuration permissions must exclude group and others (0600)");
        Properties values = new Properties();
        try (var reader = Files.newBufferedReader(path, StandardCharsets.UTF_8)) { values.load(reader); }
        Set<String> expected = new HashSet<>(KEYS);
        if (values.containsKey("adminPort")) expected.addAll(Set.of("adminPort", "adminSecret", "adminOrigin"));
        Set<String> compactionKeys = Set.of("compactionCheckSeconds", "compactionMinSeconds", "compactionGrowthBytes", "compactionGrowthRatio", "compactionZone", "compactionWindowStart", "compactionWindowEnd");
        if (values.stringPropertyNames().stream().anyMatch(compactionKeys::contains)) expected.addAll(compactionKeys);
        if (!values.stringPropertyNames().equals(expected))
            throw new IllegalArgumentException("Configuration has missing or unknown keys");
        for (String key : KEYS)
            if (values.getProperty(key).isBlank()) throw new IllegalArgumentException("Blank configuration value: " + key);
        for (String key : List.of("identitySecret", "serviceSecret", "bootstrapSecret", "fulltextSecret"))
            if (values.getProperty(key).length() < 32 || values.getProperty(key).startsWith("REPLACE_")) throw new IllegalArgumentException("Service secrets require at least 32 characters");
        if (values.containsKey("adminPort")) {
            int adminPort = Integer.parseInt(values.getProperty("adminPort"));
            if (adminPort < 1024 || adminPort > 65535 || values.getProperty("adminPort").equals(values.getProperty("port"))
                || values.getProperty("adminSecret").length() < 32)
                throw new IllegalArgumentException("Invalid administration listener configuration");
            URI origin = URI.create(values.getProperty("adminOrigin"));
            if (!"https".equals(origin.getScheme()) || origin.getHost() == null || origin.getUserInfo() != null
                || origin.getQuery() != null || origin.getFragment() != null || !origin.getPath().isEmpty())
                throw new IllegalArgumentException("Administrator origin must be an HTTPS origin");
        }
        return values;
    }

    public static void main(String[] args) throws Exception {
        if (args.length < 1 || args.length > 2 || (args.length == 2 && !args[1].equals("--init")))
            throw new IllegalArgumentException("Usage: JenaService /absolute/private/service.properties [--init]");
        Path config = Path.of(args[0]);
        if (!config.isAbsolute()) throw new IllegalArgumentException("Configuration path must be absolute");
        Properties values = settings(config);
        Path directory = Path.of(values.getProperty("dataset"));
        if (!directory.isAbsolute() || Files.isSymbolicLink(directory))
            throw new IllegalArgumentException("Dataset path must be absolute and not a symlink");
        int port = Integer.parseInt(values.getProperty("port"));
        long lifetime = Long.parseLong(values.getProperty("transactionLifetimeMillis"));
        if (port < 1024 || port > 65535 || lifetime < 100 || lifetime > 300000)
            throw new IllegalArgumentException("Port must be 1024..65535; transaction lifetime 100..300000 ms");
        URI identity = URI.create(values.getProperty("identityUrl"));
        if (!"http".equals(identity.getScheme()) || !Set.of("localhost", "127.0.0.1", "[::1]").contains(identity.getHost())
            || identity.getUserInfo() != null || identity.getFragment() != null || identity.getQuery() != null)
            throw new IllegalArgumentException("Identity verification must use a private loopback HTTP URL");
        JenaCompaction.Policy maintenancePolicy = values.containsKey("compactionCheckSeconds")
            ? new JenaCompaction.Policy(Long.parseLong(values.getProperty("compactionCheckSeconds")),
                Long.parseLong(values.getProperty("compactionMinSeconds")),
                Long.parseLong(values.getProperty("compactionGrowthBytes")),
                Double.parseDouble(values.getProperty("compactionGrowthRatio")),
                java.time.ZoneId.of(values.getProperty("compactionZone")),
                java.time.LocalTime.parse(values.getProperty("compactionWindowStart")),
                java.time.LocalTime.parse(values.getProperty("compactionWindowEnd"))) : null;
        Path marker = directory.resolve("oldap-service-format");
        if (args.length == 2) {
            // Never initialize an existing directory or seed production from a fixture.
            Files.createDirectory(directory);
            Files.setPosixFilePermissions(directory, java.nio.file.attribute.PosixFilePermissions.fromString("rwx------"));
        } else if (!Files.isRegularFile(marker) || !Files.readString(marker).equals(FORMAT)) {
            throw new IllegalArgumentException("Dataset not initialized by this service; use --init only for a new path");
        }
        // Fence before opening storage or rebuilding managed text on restart.
        if (Files.exists(directory.resolve("compaction.pending")))
            throw new IllegalStateException("Interrupted compaction requires operator verification");
        JenaSessionEngine engine = new JenaSessionEngine(directory.toString(), lifetime, false, true);
        JenaCompaction compaction = null;
        FusekiServer server = null;
        FusekiServer administration = null;
        try {
            if (args.length == 2) Files.writeString(marker, FORMAT, StandardOpenOption.CREATE_NEW);
            if (maintenancePolicy != null)
                compaction = new JenaCompaction(engine, directory, maintenancePolicy, java.time.Clock.systemUTC());
            server = FusekiServer.create().port(port).loopback(true)
                .enablePing(false).enableStats(false).enableMetrics(false).enableCompact(false).enableTasks(false)
                .addServlet("/tx/*", new JenaSessionServlet(engine, identity, values.getProperty("identitySecret"),
                    values.getProperty("serviceSecret"), values.getProperty("bootstrapSecret"), values.getProperty("fulltextSecret")))
                .addServlet("/health", new HttpServlet() {
                    @Override protected void doGet(HttpServletRequest request, HttpServletResponse response) throws IOException {
                        response.setHeader("Cache-Control", "no-store");
                        try { engine.available(); response.getWriter().write("ready\n"); }
                        catch (JenaSessionEngine.Refusal refused) { response.sendError(503); }
                    }
                }).build();
            server.getJettyServer().setStopTimeout(65000);
            server.start();
            if (values.containsKey("adminPort")) {
                administration = JenaAdministration.build(engine, Integer.parseInt(values.getProperty("adminPort")),
                    values.getProperty("adminSecret"), values.getProperty("adminOrigin"));
                administration.getJettyServer().setStopTimeout(65000);
                administration.start();
            }
            final JenaCompaction maintenance = compaction;
            if (maintenance != null) maintenance.start();
            final FusekiServer admin = administration;
            final FusekiServer running = server;
            CountDownLatch stopped = new CountDownLatch(1);
            AtomicBoolean closing = new AtomicBoolean();
            Runnable stop = () -> {
                if (!closing.compareAndSet(false, true)) return;
                try { if (maintenance != null) maintenance.close(); if (admin != null) admin.stop(); running.stop(); engine.close(); }
                catch (Exception error) { System.err.println("Backend shutdown failed; inspect storage before restart"); }
                finally { stopped.countDown(); }
            };
            Thread hook = new Thread(stop, "oldap-jena-shutdown");
            Runtime.getRuntime().addShutdownHook(hook);
            System.out.println("OLDAP Jena service ready on loopback port " + port);
            try { stopped.await(); }
            finally { stop.run(); }
        } catch (Exception failure) {
            if (compaction != null) compaction.close();
            if (administration != null) administration.stop();
            if (server != null) server.stop();
            engine.close();
            throw failure;
        }
    }
}
