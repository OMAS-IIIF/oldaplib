import java.net.*;
import java.net.http.*;
import java.nio.file.*;
import java.time.Duration;
import java.util.*;
import org.apache.jena.query.*;
import org.apache.jena.rdf.model.*;
import org.apache.jena.tdb2.TDB2Factory;
import org.apache.jena.fuseki.main.FusekiServer;

/** Run adversarial SPARQL and Graph Store requests through real embedded Fuseki. */
public class JenaProtectedDatasetProbe {
    static final String HIDDEN = "urn:probe:http-commits";
    static final String RECEIPT = "<urn:receipt> <urn:owner> \"actor-a\"";
    static Dataset storage;
    static String base;
    static final HttpClient client = HttpClient.newBuilder().connectTimeout(Duration.ofSeconds(5)).build();

    static void check(String name, boolean condition) {
        if (!condition) throw new AssertionError(name);
        System.out.println("PASS " + name);
    }
    static HttpResponse<String> request(String path, String method, String contentType, String body) throws Exception {
        return client.send(HttpRequest.newBuilder(URI.create(base + path)).timeout(Duration.ofSeconds(10))
            .header("Accept", path.equals("/query") ? "application/sparql-results+json" : "*/*")
            .header("Content-Type", contentType).method(method, HttpRequest.BodyPublishers.ofString(body)).build(),
            HttpResponse.BodyHandlers.ofString());
    }
    static boolean ask(String sparql) throws Exception {
        var response = request("/query", "POST", "application/sparql-query", sparql);
        if (response.statusCode() != 200) throw new AssertionError("Query failed: " + response.body());
        return response.body().matches("(?s).*\\\"boolean\\\"\\s*:\\s*true.*");
    }
    static HttpResponse<String> update(String sparql) throws Exception {
        return request("/update", "POST", "application/sparql-update", sparql);
    }
    static void receiptIntact(String name) {
        storage.begin(ReadWrite.READ);
        try {
            Model graph = storage.getNamedModel(HIDDEN);
            check(name, graph.size() == 1 && graph.contains(graph.createResource("urn:receipt"),
                graph.createProperty("urn:owner"), "actor-a"));
        } finally { storage.end(); }
    }
    static void seedApplication() throws Exception {
        var response = update("INSERT DATA { <urn:default> <urn:value> 1 . GRAPH <urn:app> { <urn:item> <urn:value> 2 } }");
        if (response.statusCode() / 100 != 2) throw new AssertionError(response.body());
    }

    public static void main(String[] args) throws Exception {
        if (args.length != 1 || Files.exists(Path.of(args[0]))) throw new IllegalArgumentException("Expected new dataset path");
        storage = TDB2Factory.connectDataset(args[0]);
        storage.begin(ReadWrite.WRITE);
        try {
            Model graph = storage.getNamedModel(HIDDEN);
            graph.add(graph.createResource("urn:receipt"), graph.createProperty("urn:owner"), "actor-a");
            storage.commit();
        } finally { storage.end(); }
        var visible = new ProtectedApplicationDataset(storage.asDatasetGraph(), HIDDEN);
        FusekiServer server = FusekiServer.create().port(0).loopback(true)
            .enablePing(false).enableStats(false).enableMetrics(false).enableCompact(false)
            .add("/application", visible, true).build().start();
        base = "http://localhost:" + server.getPort() + "/application";
        try {
            seedApplication();
            check("Fuseki exposes ordinary default and named application graphs", ask(
                "ASK { <urn:default> <urn:value> 1 . GRAPH <urn:app> { <urn:item> <urn:value> 2 } }"));
            for (String pattern : List.of(
                "GRAPH <" + HIDDEN + "> { ?s ?p ?o }",
                "GRAPH ?g { <urn:receipt> ?p ?o }",
                "VALUES ?g { <" + HIDDEN + "> } GRAPH ?g { ?s ?p ?o }",
                "{ SELECT * WHERE { GRAPH ?g { <urn:receipt> ?p ?o } } }")) {
                check("Receipt hidden through " + pattern, !ask("ASK { " + pattern + " }"));
            }
            check("FROM cannot expose receipt graph", !ask("ASK FROM <" + HIDDEN + "> { ?s ?p ?o }"));
            check("FROM NAMED cannot expose receipt graph", !ask("ASK FROM NAMED <" + HIDDEN + "> { GRAPH ?g { ?s ?p ?o } }"));
            check("Property path cannot expose receipt", !ask("ASK { GRAPH ?g { <urn:receipt> <urn:owner>+ ?o } }"));
            check("ARQ union graph cannot expose receipt", !ask("ASK { GRAPH <urn:x-arq:UnionGraph> { <urn:receipt> ?p ?o } }"));

            for (String command : List.of(
                "INSERT DATA { GRAPH <" + HIDDEN + "> { <urn:fake> <urn:owner> 'actor-b' } }",
                "DELETE DATA { GRAPH <" + HIDDEN + "> { " + RECEIPT + " } }",
                "DELETE WHERE { GRAPH <" + HIDDEN + "> { ?s ?p ?o } }",
                "INSERT { GRAPH ?g { <urn:fake> <urn:owner> 'actor-b' } } WHERE { VALUES ?g { <" + HIDDEN + "> } }",
                "CLEAR GRAPH <" + HIDDEN + ">",
                "DROP SILENT GRAPH <" + HIDDEN + ">",
                "COPY GRAPH <urn:app> TO GRAPH <" + HIDDEN + ">",
                "MOVE GRAPH <urn:app> TO GRAPH <" + HIDDEN + ">",
                "ADD GRAPH <urn:app> TO GRAPH <" + HIDDEN + ">",
                "COPY SILENT GRAPH <" + HIDDEN + "> TO GRAPH <urn:app>",
                "MOVE SILENT GRAPH <" + HIDDEN + "> TO GRAPH <urn:app>",
                "ADD SILENT GRAPH <" + HIDDEN + "> TO GRAPH <urn:app>",
                "CLEAR ALL", "DROP ALL", "CLEAR NAMED",
                "DELETE { GRAPH ?g { ?s ?p ?o } } WHERE { GRAPH ?g { ?s ?p ?o } }")) {
                seedApplication();
                update(command); // Some no-match/SILENT operations legitimately succeed.
                receiptIntact("Receipt survives " + command);
                if (command.endsWith("TO GRAPH <urn:app>"))
                    check("No copied receipt after " + command, !ask("ASK { GRAPH ?g { <urn:receipt> ?p ?o } }"));
            }
            seedApplication();
            var cleared = update("CLEAR ALL");
            check("Application CLEAR ALL still removes visible data", cleared.statusCode() / 100 == 2
                && !ask("ASK { { ?s ?p ?o } UNION { GRAPH ?g { ?s ?p ?o } } }"));
            receiptIntact("Successful bulk clear leaves internal receipt intact");
            var failed = update("INSERT DATA { GRAPH <urn:app> { <urn:partial> <urn:value> 3 } }; "
                + "INSERT DATA { GRAPH <" + HIDDEN + "> { <urn:fake> <urn:owner> 'actor-b' } }");
            check("Rejected mixed request rolls back earlier application writes", failed.statusCode() >= 400
                && !ask("ASK { GRAPH <urn:app> { <urn:partial> ?p ?o } }"));
            receiptIntact("Rejected mixed request preserves receipt");

            String graphPath = "/data?graph=" + URLEncoder.encode(HIDDEN, java.nio.charset.StandardCharsets.UTF_8);
            var hiddenGet = request(graphPath, "GET", "text/turtle", "");
            check("Graph Store GET cannot expose reserved receipt", hiddenGet.statusCode() == 404
                || (hiddenGet.statusCode() == 200 && !hiddenGet.body().contains("actor-a")));
            for (String method : List.of("PUT", "POST", "DELETE")) {
                request(graphPath, method, "text/turtle", method.equals("DELETE") ? "" : "<urn:fake> <urn:owner> 'actor-b' .");
                receiptIntact("Graph Store " + method + " cannot modify receipt");
            }
            // Graph APIs must also return the view, never an underlying graph.
            visible.begin(ReadWrite.READ);
            try {
                check("Union graph excludes receipt triples", !visible.getUnionGraph().contains(
                    org.apache.jena.graph.NodeFactory.createURI("urn:receipt"), org.apache.jena.graph.Node.ANY, org.apache.jena.graph.Node.ANY));
            } finally { visible.end(); }
        } finally {
            server.stop();
            storage.close();
        }
    }
}
