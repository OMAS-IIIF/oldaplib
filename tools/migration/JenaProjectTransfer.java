import java.io.ByteArrayOutputStream;
import java.nio.charset.StandardCharsets;
import java.util.*;
import org.apache.jena.atlas.json.*;
import org.apache.jena.graph.*;
import org.apache.jena.query.*;
import org.apache.jena.riot.*;
import org.apache.jena.riot.out.NodeFmtLib;

/** Native RDF 1.2 project transfer within the caller's transaction.
 * Raw graphs bypass resource ACLs, so every call rechecks current root permission.
 * Only registered project model/list/data/history graphs are eligible; administration,
 * receipts and default graphs are never imported or exported by this boundary.
 */
final class JenaProjectTransfer {
    static final String PREFIX = "PREFIX oldap: <http://oldap.org/base#> "
        + "PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> ";

    static Set<Node> graphs(Dataset dataset, String actor, JsonObject request, boolean importing) {
        Set<String> keys = importing ? Set.of("project", "parts", "trig") : Set.of("project", "parts");
        if (!request.keys().equals(keys)) throw new JenaSessionEngine.Refusal(400, "Invalid transfer request");
        String user = NodeFmtLib.strNT(NodeFactory.createURI(actor));
        String authorization = PREFIX + "ASK { GRAPH oldap:admin { " + user
            + " oldap:inProject oldap:SystemProject . ?grant rdf:reifies <<( " + user
            + " oldap:inProject oldap:SystemProject )>> ; oldap:hasAdminPermission oldap:ADMIN_OLDAP . } }";
        try (QueryExecution query = QueryExecutionFactory.create(authorization, dataset)) {
            if (!query.execAsk()) throw new JenaSessionEngine.Refusal(403, "Root administration required for raw transfer");
        }
        String project = request.getString("project");
        if (project == null || !project.matches("[A-Za-z_][A-Za-z0-9_.-]*") || Set.of("oldap", "shared").contains(project))
            throw new JenaSessionEngine.Refusal(400, "Expected an ordinary project short name");
        String namespace;
        try (QueryExecution query = QueryExecutionFactory.create(PREFIX
                + "SELECT DISTINCT ?namespace WHERE { GRAPH oldap:admin { ?p a oldap:Project ; "
                + "oldap:projectShortName ?name ; oldap:namespaceIri ?namespace . FILTER(STR(?name) = \""
                + project + "\") } }", dataset)) {
            ResultSet rows = query.execSelect();
            if (!rows.hasNext()) throw new JenaSessionEngine.Refusal(400, "Target project must already exist");
            namespace = rows.next().getResource("namespace").getURI();
            if (rows.hasNext()) throw new JenaSessionEngine.Refusal(400, "Ambiguous project namespace");
        }
        Set<Node> graphs = new LinkedHashSet<>();
        for (JsonValue value : request.get("parts").getAsArray()) {
            String part = value.getAsString().value();
            if (!Set.of("data", "history", "shacl", "onto", "lists").contains(part))
                throw new JenaSessionEngine.Refusal(400, "Unsupported project graph");
            graphs.add(NodeFactory.createURI(namespace + part));
        }
        return graphs;
    }

    /** Serialize all selected graphs together, preserving cross-graph blank nodes. */
    static String exportGraphs(Dataset source, String actor, String body) {
        Set<Node> graphs = graphs(source, actor, JSON.parse(body), false);
        Dataset copy = DatasetFactory.create();
        try {
            for (Node graph : graphs)
                source.asDatasetGraph().find(graph, Node.ANY, Node.ANY, Node.ANY).forEachRemaining(copy.asDatasetGraph()::add);
            ByteArrayOutputStream out = new ByteArrayOutputStream();
            RDFDataMgr.write(out, copy, Lang.TRIG);
            return out.toString(StandardCharsets.UTF_8);
        } finally { copy.close(); }
    }

    /** Parse and validate the entire payload before adding any quad; never replace graphs. */
    static String importGraphs(Dataset target, String actor, String body) {
        JsonObject request = JSON.parse(body);
        Set<Node> graphs = graphs(target, actor, request, true);
        Dataset parsed = DatasetFactory.create();
        try {
            try {
                RDFParser.fromString(request.getString("trig"), Lang.TRIG).checking(true).parse(parsed);
            } catch (RiotException error) {
                throw new JenaSessionEngine.Refusal(400, "Invalid TriG payload");
            }
            parsed.asDatasetGraph().find().forEachRemaining(quad -> {
                if (!graphs.contains(quad.getGraph()))
                    throw new JenaSessionEngine.Refusal(400, "Payload contains a graph outside the selected project scope");
            });
            parsed.asDatasetGraph().find().forEachRemaining(target.asDatasetGraph()::add);
            return "imported";
        } finally { parsed.close(); }
    }
}
