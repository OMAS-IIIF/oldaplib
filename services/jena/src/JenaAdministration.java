import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.Iterator;
import jakarta.servlet.*;
import jakarta.servlet.http.*;
import org.apache.jena.fuseki.main.FusekiServer;
import org.apache.jena.fuseki.mod.admin.ActionServerStatus;
import org.apache.jena.fuseki.mgt.ActionDatasets;
import org.apache.jena.fuseki.validation.*;
import org.apache.jena.graph.*;
import org.apache.jena.query.*;
import org.apache.jena.riot.system.PrefixMap;
import org.apache.jena.sparql.core.*;
import org.apache.jena.sparql.util.Context;

/** Official Fuseki UI and protocols over the service-owned application dataset.
 *
 * The second listener is private to the Docker bridge. The authenticated reverse
 * proxy supplies a separate administrator secret; no normal OLDAP token grants
 * access. Native Fuseki handles SPARQL, graph-store uploads, validation and stats.
 * Dataset creation/deletion/compaction remain service lifecycle operations.
 */
public final class JenaAdministration {
    private JenaAdministration() {}

    /** Build without opening storage again or copying/modifying Apache UI assets. */
    static FusekiServer build(JenaSessionEngine engine, int port, String secret, String origin) {
        String resource = JenaAdministration.class.getResource("/webapp/index.html").toString();
        String webapp = resource.substring(0, resource.lastIndexOf('/'));
        byte[] expected = secret.getBytes(StandardCharsets.UTF_8);
        return FusekiServer.create().port(port)
            .staticFileBase(webapp).enableCors(false)
            .enablePing(true).enableStats(true).enableMetrics(false)
            .enableTasks(false).enableCompact(false)
            .add("/oldap", new LiveDataset(engine), true)
            .addServlet("/$/server", new ActionServerStatus())
            .addServlet("/$/datasets/*", new ActionDatasets())
            .addServlet("/$/validate/query", new QueryValidator())
            .addServlet("/$/validate/update", new UpdateValidator())
            .addServlet("/$/validate/data", new DataValidator())
            .addServlet("/$/validate/iri", new IRIValidator())
            .addServlet("/$/validate/langtag", new LangTagValidator())
            .addFilter("/*", (request, response, chain) -> {
                HttpServletRequest req = (HttpServletRequest)request;
                HttpServletResponse res = (HttpServletResponse)response;
                String supplied = req.getHeader("X-Oldap-Admin-Key");
                if (supplied == null || !MessageDigest.isEqual(expected, supplied.getBytes(StandardCharsets.UTF_8))) {
                    res.sendError(401); return;
                }
                res.setHeader("Cache-Control", "no-store");
                res.setHeader("X-Content-Type-Options", "nosniff");
                res.setHeader("X-Frame-Options", "DENY");
                String path = req.getRequestURI();
                boolean read = req.getMethod().equals("GET") || req.getMethod().equals("HEAD");
                if (!read && !origin.equals(req.getHeader("Origin"))) {
                    res.sendError(403, "Same-origin requests only"); return;
                }
                // Dataset lifecycle belongs to OLDAP, not to the web console.
                if (path.startsWith("/$/datasets") && !read) {
                    res.sendError(403, "Dataset lifecycle is managed by OLDAP deployment"); return;
                }
                // Pin the current managed-text view for the entire native request.
                // Index replacement uses the exclusive side of this same lock.
                engine.maintenance.readLock().lock();
                try {
                    engine.available();
                    chain.doFilter(request, response);
                } catch (JenaSessionEngine.Refusal refused) {
                    res.sendError(refused.status);
                } finally { engine.maintenance.readLock().unlock(); }
            }).build();
    }

    /** Resolve the current protected/text-indexed view under the request lock.
     * Never expose a transparent wrapper that an optimizer could unwrap. Native
     * transactions use the SAME TDB writer lock as API transactions. Closing a
     * Fuseki endpoint must never close the engine's storage or text index.
     */
    static final class LiveDataset extends DatasetGraphBase {
        private final JenaSessionEngine engine;
        LiveDataset(JenaSessionEngine engine) { this.engine = engine; }
        private DatasetGraph current() { return engine.application.asDatasetGraph(); }
        @Override public Graph getDefaultGraph() { return GraphView.createDefaultGraph(this); }
        @Override public Graph getUnionGraph() { return GraphView.createUnionGraph(this); }
        @Override public Graph getGraph(Node graph) {
            if (Quad.isDefaultGraph(graph)) return getDefaultGraph();
            if (Quad.isUnionGraph(graph)) return getUnionGraph();
            return GraphView.createNamedGraph(this, graph);
        }
        @Override public Iterator<Node> listGraphNodes() { return current().listGraphNodes(); }
        @Override public Iterator<Quad> find(Node g, Node s, Node p, Node o) { return current().find(g, s, p, o); }
        @Override public Iterator<Quad> findNG(Node g, Node s, Node p, Node o) { return current().findNG(g, s, p, o); }
        @Override public void add(Quad q) { current().add(q); }
        @Override public void delete(Quad q) { current().delete(q); }
        @Override public void add(Node g, Node s, Node p, Node o) { current().add(g, s, p, o); }
        @Override public void delete(Node g, Node s, Node p, Node o) { current().delete(g, s, p, o); }
        @Override public void deleteAny(Node g, Node s, Node p, Node o) { current().deleteAny(g, s, p, o); }
        @Override public void addGraph(Node g, Graph graph) { current().addGraph(g, graph); }
        @Override public void removeGraph(Node g) { current().removeGraph(g); }
        @Override public PrefixMap prefixes() { return current().prefixes(); }
        @Override public Context getContext() { return current().getContext(); }
        @Override public void begin(TxnType type) { current().begin(type); }
        @Override public boolean promote(Promote mode) { return current().promote(mode); }
        @Override public void commit() { current().commit(); }
        @Override public void abort() { current().abort(); }
        @Override public void end() { current().end(); }
        @Override public ReadWrite transactionMode() { return current().transactionMode(); }
        @Override public TxnType transactionType() { return current().transactionType(); }
        @Override public boolean isInTransaction() { return current().isInTransaction(); }
        @Override public boolean supportsTransactions() { return true; }
        @Override public boolean supportsTransactionAbort() { return true; }
        @Override public void close() { /* The service owns storage. */ }
    }
}
