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
 * Private authenticated servlet shared by the service and diagnostic probe.
 * The trusted Python peer validates OLDAP tokens with the existing TokenCodec.
 * Java checks service access and consumes only the peer's verified user IRI;
 * no JWT/password/role logic is copied here. Never expose this transport publicly.
 */
public class JenaSessionServlet extends HttpServlet {
    final JenaSessionEngine engine;
    final HttpClient verifier = HttpClient.newBuilder().connectTimeout(Duration.ofSeconds(2)).build();
    final URI verificationUrl;
    final String verificationSecret;
    final String serviceSecret;
    final String bootstrapSecret;
    final String fulltextSecret;

    /** Private transport credentials are separate from end-user authorization. */
    JenaSessionServlet(JenaSessionEngine engine, URI verificationUrl, String verificationSecret,
                       String serviceSecret, String bootstrapSecret, String fulltextSecret) {
        this.engine = engine;
        this.verificationUrl = verificationUrl;
        this.verificationSecret = verificationSecret;
        this.serviceSecret = serviceSecret;
        this.bootstrapSecret = bootstrapSecret;
        this.fulltextSecret = fulltextSecret;
        if (verificationUrl == null || verificationSecret == null || verificationSecret.isBlank()
            || serviceSecret == null || serviceSecret.isBlank())
            throw new IllegalArgumentException("Explicit service credentials required");
    }

    /** Production has no failure injection or debug output. Probe subclasses opt in. */
    String fulltextFault(HttpServletRequest request) { return null; }
    String commitFault(HttpServletRequest request) { return null; }
    void reportFailure(Throwable error) { }

    @Override protected void service(HttpServletRequest request, HttpServletResponse response) throws IOException {
        response.setHeader("Cache-Control", "no-store");
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

    /** Probe-only timing extension; the service emits no diagnostic headers. */
    void writeTimings(HttpServletRequest request, HttpServletResponse response, long authentication, long dispatch) { }

    @Override protected void doPost(HttpServletRequest request, HttpServletResponse response) throws IOException {
        try {
            long authenticationStart = System.nanoTime();
            if ("/bootstrap".equals(request.getPathInfo())) {
                // Credential login has no user token yet. A separate backend
                // credential permits read-only initialization, never mutations.
                authenticateService(request);
                String expected = bootstrapSecret;
                String supplied = request.getHeader("X-Oldap-Bootstrap-Key");
                if (expected == null || expected.isBlank() || supplied == null
                    || !MessageDigest.isEqual(expected.getBytes(StandardCharsets.UTF_8), supplied.getBytes(StandardCharsets.UTF_8)))
                    throw new JenaSessionEngine.Refusal(401, "Invalid bootstrap credentials");
                byte[] bytes = request.getInputStream().readNBytes(262145);
                if (bytes.length > 262144) throw new JenaSessionEngine.Refusal(413, "Request too large");
                long authenticationNanos = System.nanoTime() - authenticationStart;
                long dispatchStart = System.nanoTime();
                String result = engine.dispatch("READ", UUID.randomUUID(), "bootstrap", new String(bytes, StandardCharsets.UTF_8));
                writeTimings(request, response, authenticationNanos, System.nanoTime() - dispatchStart);
                response.setContentType("application/sparql-results+json; charset=UTF-8");
                response.getWriter().write(result);
                return;
            }
            String identity = authenticate(request);
            long authenticationNanos = System.nanoTime() - authenticationStart;
            String[] path = request.getPathInfo().split("/");
            if (path.length != 3) throw new JenaSessionEngine.Refusal(404, "Expected /operation/uuid");
            String operation = path[1];
            UUID id = UUID.fromString(path[2]);
            byte[] bytes = request.getInputStream().readNBytes(262145);
            if (bytes.length > 262144) throw new JenaSessionEngine.Refusal(413, "Request too large");
            if (Set.of("FULLTEXT_STATE", "FULLTEXT_APPLY").contains(operation)) {
                // This is a service maintenance capability, not an OLDAP role.
                // Public API model-admin authorization must precede its future use.
                String expected = fulltextSecret;
                String supplied = request.getHeader("X-Oldap-Fulltext-Admin-Key");
                if (expected == null || expected.isBlank() || supplied == null
                    || !MessageDigest.isEqual(expected.getBytes(StandardCharsets.UTF_8), supplied.getBytes(StandardCharsets.UTF_8)))
                    throw new JenaSessionEngine.Refusal(403, "Fulltext administration credential required");
                String injection = fulltextFault(request);
                long dispatchStart = System.nanoTime();
                String result = engine.fulltext(operation, new String(bytes, StandardCharsets.UTF_8), injection);
                writeTimings(request, response, authenticationNanos, System.nanoTime() - dispatchStart);
                response.setContentType("application/json; charset=UTF-8");
                response.setHeader("Cache-Control", "no-store");
                response.getWriter().write(result);
                return;
            }
            String fault = commitFault(request);
            // Test-only fault injection: 503 models an unavailable commit response.
            if (operation.equals("COMMIT") && "before".equals(fault)) {
                response.sendError(503);
                return;
            }
            long dispatchStart = System.nanoTime();
            String result = engine.dispatch(operation, id, identity, new String(bytes, StandardCharsets.UTF_8));
            // Opt-in diagnostics on this isolated authenticated probe only.
            // Dispatch includes parsing, dataset access and result serialization;
            // it must not be described as pure query evaluation time.
            writeTimings(request, response, authenticationNanos, System.nanoTime() - dispatchStart);
            if (operation.equals("COMMIT") && "yes".equals(fault)) {
                response.sendError(503);
                return;
            }
            response.setContentType("text/plain; charset=UTF-8");
            response.getWriter().write(result);
        } catch (Exception error) {
            Throwable cause = error instanceof ExecutionException ? error.getCause() : error;
            reportFailure(cause);
            int status = cause instanceof JenaSessionEngine.Refusal refusal ? refusal.status :
                cause instanceof IOException ? 503 : 400;
            response.sendError(status, cause instanceof JenaSessionEngine.Refusal ? cause.getMessage() : "Invalid request");
        }
    }

}
