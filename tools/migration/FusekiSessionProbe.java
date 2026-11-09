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

/** Isolated test entry point. Fault injection is absent from the built service. */
public class FusekiSessionProbe extends JenaSessionServlet {
    FusekiSessionProbe(JenaSessionEngine engine) {
        super(engine, URI.create(System.getenv("PROBE_IDENTITY_URL")),
              System.getenv("PROBE_IDENTITY_SECRET"), System.getenv("PROBE_TRANSPORT_SECRET"),
              System.getenv("PROBE_BOOTSTRAP_SECRET"), System.getenv("PROBE_FULLTEXT_ADMIN_SECRET"));
    }

    @Override String fulltextFault(HttpServletRequest request) {
        return "yes".equals(System.getenv("PROBE_FULLTEXT_FAULTS"))
            ? request.getHeader("X-Probe-Fulltext-Failure") : null;
    }
    @Override String commitFault(HttpServletRequest request) { return request.getHeader("X-Probe-Lose-Reply"); }
    @Override void reportFailure(Throwable error) {
        if ("yes".equals(System.getenv("PROBE_FULLTEXT_FAULTS"))) error.printStackTrace(System.err);
    }
    @Override void writeTimings(HttpServletRequest request, HttpServletResponse response, long authentication, long dispatch) {
        if ("yes".equals(request.getHeader("X-Probe-Timing"))) {
            response.setHeader("X-Probe-Authentication-Nanos", Long.toString(authentication));
            response.setHeader("X-Probe-Dispatch-Nanos", Long.toString(dispatch));
        }
    }

    public static void main(String[] args) throws Exception {
        if (args.length != 3 || !Set.of("new", "reopen").contains(args[1]))
            throw new IllegalArgumentException("Expected directory, new/reopen, lifetime milliseconds");
        if (Files.exists(Path.of(args[0])) != args[1].equals("reopen"))
            throw new IllegalArgumentException("Unexpected dataset existence");
        try (var engine = new JenaSessionEngine(args[0], Long.parseLong(args[2]), "yes".equals(System.getenv("PROBE_TEXT_FIXTURE")))) {
            // Test-only seeding from explicit local fixtures before any HTTP access.
            String seeds = System.getenv("PROBE_SEED_FILES");
            if (seeds != null) {
                if (!args[1].equals("new")) throw new IllegalArgumentException("Cannot seed a reopened dataset");
                engine.dataset.begin(org.apache.jena.query.ReadWrite.WRITE);
                try {
                    for (String file : seeds.split("\\n"))
                        org.apache.jena.riot.RDFDataMgr.read(engine.dataset, file);
                    if ("yes".equals(System.getenv("PROBE_TEXT_FIXTURE"))) {
                        // A known private canary verifies that text lookup cannot
                        // bypass the receipt view through a separately held index.
                        engine.dataset.getNamedModel(JenaSessionEngine.RECEIPTS)
                            .createResource("urn:private-text-canary")
                            .addProperty(org.apache.jena.rdf.model.ResourceFactory.createProperty("http://oldap.org/test#name"),
                                "ReceiptTextMarker");
                    }
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
