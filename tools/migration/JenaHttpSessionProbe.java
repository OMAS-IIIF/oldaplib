import com.sun.net.httpserver.*;
import java.io.*;
import java.net.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.util.*;
import java.util.concurrent.*;

/** Legacy loopback transport retained to regression-test the shared engine. */
public class JenaHttpSessionProbe extends JenaSessionEngine {
    final Map<String, String> identities;
    JenaHttpSessionProbe(String directory, long lifetimeMillis) {
        super(directory, lifetimeMillis);
        identities = Map.of(System.getenv("PROBE_TOKEN_A"), "actor-a",
                            System.getenv("PROBE_TOKEN_B"), "actor-b");
    }

    void handle(HttpExchange exchange) throws IOException {
        int status = 200;
        String response;
        try {
            String authorization = exchange.getRequestHeaders().getFirst("Authorization");
            String identity = authorization == null ? null : identities.get(authorization);
            if (identity == null) throw new Refusal(401, "Unknown probe identity");
            if (!exchange.getRequestMethod().equals("POST")) throw new Refusal(405, "POST required");
            String[] path = exchange.getRequestURI().getPath().split("/");
            if (path.length != 3) throw new Refusal(404, "Expected /operation/uuid");
            String operation = path[1];
            UUID id = UUID.fromString(path[2]);
            byte[] bytes = exchange.getRequestBody().readNBytes(262145);
            if (bytes.length > 262144) throw new Refusal(413, "Probe request too large");
            String body = new String(bytes, StandardCharsets.UTF_8);
            if (operation.equals("COMMIT") && "before".equals(exchange.getRequestHeaders().getFirst("X-Probe-Lose-Reply"))) {
                exchange.close();
                return;
            }
            response = dispatch(operation, id, identity, body);
            if (operation.equals("COMMIT") && "yes".equals(exchange.getRequestHeaders().getFirst("X-Probe-Lose-Reply"))) {
                exchange.close(); // Test-only fault: durable commit, no HTTP response.
                return;
            }
        } catch (Exception error) {
            Throwable cause = error instanceof ExecutionException ? error.getCause() : error;
            status = cause instanceof Refusal refusal ? refusal.status : 400;
            response = cause.getMessage() == null ? "Invalid request" : cause.getMessage();
        }
        byte[] bytes = response.getBytes(StandardCharsets.UTF_8);
        exchange.sendResponseHeaders(status, bytes.length);
        try (OutputStream output = exchange.getResponseBody()) { output.write(bytes); }
    }

    public static void main(String[] args) throws Exception {
        if (args.length != 3 || !Set.of("new", "reopen").contains(args[1]))
            throw new IllegalArgumentException("Expected directory, new/reopen, lifetime milliseconds");
        if (Files.exists(Path.of(args[0])) != args[1].equals("reopen"))
            throw new IllegalArgumentException("Unexpected dataset existence");
        JenaHttpSessionProbe probe = new JenaHttpSessionProbe(args[0], Long.parseLong(args[2]));
        HttpServer server = HttpServer.create(new InetSocketAddress(InetAddress.getLoopbackAddress(), 0), 8);
        // Bound both handler concurrency and queued requests in this experiment.
        ExecutorService handlers = new ThreadPoolExecutor(4, 4, 0, TimeUnit.SECONDS,
            new ArrayBlockingQueue<>(16), new ThreadPoolExecutor.AbortPolicy());
        server.setExecutor(handlers);
        server.createContext("/", probe::handle);
        server.start();
        System.out.println(server.getAddress().getPort());
        System.out.flush();
        try { while (System.in.read() != -1) { /* parent process lifetime */ } }
        finally {
            server.stop(0);
            handlers.shutdownNow();
            probe.close();
        }
    }
}
