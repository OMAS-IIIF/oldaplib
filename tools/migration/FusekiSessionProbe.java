import jakarta.servlet.http.*;
import java.io.*;
import java.net.*;
import java.net.http.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.security.MessageDigest;
import java.time.Duration;
import java.util.*;
import java.util.concurrent.ExecutionException;
import org.apache.jena.atlas.json.JSON;
import org.apache.jena.fuseki.main.FusekiServer;

/**
 * Isolated Fuseki servlet experiment with the shared transaction engine.
 * The trusted Python peer validates OLDAP tokens with the existing TokenCodec.
 * Java checks service access and consumes only the peer's verified user IRI;
 * no JWT/password/role logic is copied here. Never expose this probe publicly.
 */
public class FusekiSessionProbe extends HttpServlet {
    final JenaSessionEngine engine;
    final HttpClient verifier = HttpClient.newBuilder().connectTimeout(Duration.ofSeconds(2)).build();
    final URI verificationUrl = URI.create(System.getenv("PROBE_IDENTITY_URL"));
    final String verificationSecret = System.getenv("PROBE_IDENTITY_SECRET");
    final String serviceSecret = System.getenv("PROBE_TRANSPORT_SECRET");

    FusekiSessionProbe(JenaSessionEngine engine) {
        this.engine = engine;
        if (verificationSecret == null || verificationSecret.isBlank()
            || serviceSecret == null || serviceSecret.isBlank())
            throw new IllegalArgumentException("Explicit probe service credentials required");
    }

    @Override protected void service(HttpServletRequest request, HttpServletResponse response) throws IOException {
        // Do not inherit TRACE/OPTIONS behavior on the private credential route.
        if (!request.getMethod().equals("POST")) { response.sendError(405); return; }
        doPost(request, response);
    }

    /** Check backend service credentials, separately from any OLDAP user. */
    void authenticateService(HttpServletRequest request) {
        String supplied = request.getHeader("X-Oldap-Service-Key");
        if (supplied == null || !MessageDigest.isEqual(serviceSecret.getBytes(StandardCharsets.UTF_8),
                                                      supplied.getBytes(StandardCharsets.UTF_8)))
            throw new JenaSessionEngine.Refusal(401, "Invalid service credentials");
    }

    /** Fail closed on invalid credentials OR unavailable/malformed verification. */
    String authenticate(HttpServletRequest request) throws Exception {
        authenticateService(request);
        String authorization = request.getHeader("Authorization");
        if (authorization == null || !authorization.startsWith("Bearer ") || authorization.length() > 8192)
            throw new JenaSessionEngine.Refusal(401, "Invalid access token");
        var validation = HttpRequest.newBuilder(verificationUrl).timeout(Duration.ofSeconds(2))
            .header("Authorization", "Bearer " + verificationSecret)
            .header("Content-Type", "application/x-www-form-urlencoded")
            .POST(HttpRequest.BodyPublishers.ofString("token=" + URLEncoder.encode(
                authorization.substring(7), StandardCharsets.UTF_8))).build();
        try {
            var response = verifier.send(validation, HttpResponse.BodyHandlers.ofString());
            if (response.statusCode() != 200 || response.body().length() > 16384)
                throw new IllegalStateException("Identity service response invalid");
            var identity = JSON.parse(response.body());
            if (!identity.getBoolean("active")) throw new JenaSessionEngine.Refusal(401, "Invalid access token");
            String actor = identity.getString("sub");
            if (actor == null || !URI.create(actor).isAbsolute()) throw new IllegalStateException("Invalid verified actor");
            return actor;
        } catch (JenaSessionEngine.Refusal refusal) { throw refusal; }
        catch (Exception error) { throw new JenaSessionEngine.Refusal(503, "Identity verification unavailable"); }
    }

    @Override protected void doPost(HttpServletRequest request, HttpServletResponse response) throws IOException {
        try {
            if ("/bootstrap".equals(request.getPathInfo())) {
                // Credential login has no user token yet. A separate backend
                // credential permits read-only initialization, never mutations.
                authenticateService(request);
                String expected = System.getenv("PROBE_BOOTSTRAP_SECRET");
                String supplied = request.getHeader("X-Oldap-Bootstrap-Key");
                if (expected == null || expected.isBlank() || supplied == null
                    || !MessageDigest.isEqual(expected.getBytes(StandardCharsets.UTF_8), supplied.getBytes(StandardCharsets.UTF_8)))
                    throw new JenaSessionEngine.Refusal(401, "Invalid bootstrap credentials");
                byte[] bytes = request.getInputStream().readNBytes(262145);
                if (bytes.length > 262144) throw new JenaSessionEngine.Refusal(413, "Probe request too large");
                String result = engine.dispatch("READ", UUID.randomUUID(), "bootstrap", new String(bytes, StandardCharsets.UTF_8));
                response.setContentType("application/sparql-results+json; charset=UTF-8");
                response.getWriter().write(result);
                return;
            }
            String identity = authenticate(request);
            String[] path = request.getPathInfo().split("/");
            if (path.length != 3) throw new JenaSessionEngine.Refusal(404, "Expected /operation/uuid");
            String operation = path[1];
            UUID id = UUID.fromString(path[2]);
            byte[] bytes = request.getInputStream().readNBytes(262145);
            if (bytes.length > 262144) throw new JenaSessionEngine.Refusal(413, "Probe request too large");
            String fault = request.getHeader("X-Probe-Lose-Reply");
            // Test-only fault injection: 503 models an unavailable commit response.
            if (operation.equals("COMMIT") && "before".equals(fault)) {
                response.sendError(503);
                return;
            }
            String result = engine.dispatch(operation, id, identity, new String(bytes, StandardCharsets.UTF_8));
            if (operation.equals("COMMIT") && "yes".equals(fault)) {
                response.sendError(503);
                return;
            }
            response.setContentType("text/plain; charset=UTF-8");
            response.getWriter().write(result);
        } catch (Exception error) {
            Throwable cause = error instanceof ExecutionException ? error.getCause() : error;
            int status = cause instanceof JenaSessionEngine.Refusal refusal ? refusal.status : 400;
            response.sendError(status, cause instanceof JenaSessionEngine.Refusal ? cause.getMessage() : "Invalid request");
        }
    }

    public static void main(String[] args) throws Exception {
        if (args.length != 3 || !Set.of("new", "reopen").contains(args[1]))
            throw new IllegalArgumentException("Expected directory, new/reopen, lifetime milliseconds");
        if (Files.exists(Path.of(args[0])) != args[1].equals("reopen"))
            throw new IllegalArgumentException("Unexpected dataset existence");
        try (var engine = new JenaSessionEngine(args[0], Long.parseLong(args[2]))) {
            // Test-only seeding from explicit local fixtures before any HTTP access.
            String seeds = System.getenv("PROBE_SEED_FILES");
            if (seeds != null) {
                if (!args[1].equals("new")) throw new IllegalArgumentException("Cannot seed a reopened dataset");
                engine.dataset.begin(org.apache.jena.query.ReadWrite.WRITE);
                try {
                    for (String file : seeds.split("\\n"))
                        org.apache.jena.riot.RDFDataMgr.read(engine.dataset, file);
                    engine.dataset.commit();
                } finally { engine.dataset.end(); }
            }
            // Only the servlet is mounted. No raw query/update/admin dataset route
            // can bypass actor verification, writer admission or receipt protection.
            var server = FusekiServer.create().port(0).loopback(true)
                .enablePing(false).enableStats(false).enableMetrics(false).enableCompact(false)
                .enableTasks(false).addServlet("/tx/*", new FusekiSessionProbe(engine)).build().start();
            try {
                System.out.println(server.getPort());
                System.out.flush();
                while (System.in.read() != -1) { /* owned process lifetime */ }
            } finally { server.stop(); }
        }
    }
}
