import java.io.*;
import java.nio.file.*;
import org.apache.jena.atlas.json.*;
import org.apache.jena.query.*;
import org.apache.jena.riot.*;
import org.apache.jena.tdb2.TDB2Factory;
import org.apache.jena.update.UpdateAction;

/** Local JSON-line bridge for testing real library queries on owned TDB2 data.
 * Args: new dataset directory. No listeners, credentials, or installed service.
 * Each response wraps a query result; errors terminate the probe immediately.
 */
public class JenaModelProbe {
    public static void main(String[] args) throws Exception {
        if (args.length != 1 || Files.exists(Path.of(args[0])))
            throw new IllegalArgumentException("Expected new owned dataset path");
        Dataset dataset = TDB2Factory.connectDataset(args[0]);
        try (BufferedReader input = new BufferedReader(new InputStreamReader(System.in))) {
            String line;
            while ((line = input.readLine()) != null) {
                JsonObject request = JSON.parse(line), response = new JsonObject();
                String operation = request.getString("operation");
                switch (operation) {
                    case "begin" -> dataset.begin(ReadWrite.WRITE);
                    case "commit" -> { dataset.commit(); dataset.end(); }
                    case "abort" -> { dataset.abort(); dataset.end(); }
                    case "update" -> UpdateAction.parseExecute(request.getString("query"), dataset);
                    case "load" -> RDFDataMgr.read(dataset, request.getString("path"));
                    case "export" -> {
                        boolean own = !dataset.isInTransaction();
                        if (own) dataset.begin(ReadWrite.READ);
                        try (OutputStream out = Files.newOutputStream(Path.of(request.getString("path")), StandardOpenOption.CREATE_NEW)) {
                            Dataset selected = DatasetFactory.create();
                            String graph = request.getString("graph");
                            selected.addNamedModel(graph, dataset.getNamedModel(graph));
                            RDFDataMgr.write(out, selected, Lang.TRIG);
                        } finally { if (own) dataset.end(); }
                    }
                    case "explain" -> {
                        // Algebra only: no service access or mutation; useful for
                        // verifying correlated filter placement in acceptance tests.
                        var query = QueryFactory.create(request.getString("query"));
                        response.put("result", org.apache.jena.sparql.algebra.Algebra.optimize(
                            org.apache.jena.sparql.algebra.Algebra.compile(query)).toString());
                    }
                    case "query" -> {
                        boolean own = !dataset.isInTransaction();
                        if (own) dataset.begin(ReadWrite.READ);
                        try (QueryExecution execution = QueryExecutionFactory.create(request.getString("query"), dataset)) {
                            ByteArrayOutputStream out = new ByteArrayOutputStream();
                            if (execution.getQuery().isConstructType()) {
                                RDFDataMgr.write(out, execution.execConstruct(), Lang.TURTLE);
                                response.put("format", "turtle");
                            } else if (execution.getQuery().isAskType()) {
                                ResultSetFormatter.outputAsJSON(out, execution.execAsk());
                            } else {
                                ResultSetFormatter.outputAsJSON(out, execution.execSelect());
                            }
                            response.put("result", out.toString(java.nio.charset.StandardCharsets.UTF_8));
                        } finally { if (own) dataset.end(); }
                    }
                    default -> throw new IllegalArgumentException("Unsupported operation");
                }
                System.out.println(JSON.toStringFlat(response));
                System.out.flush();
            }
            if (dataset.isInTransaction()) { dataset.abort(); dataset.end(); }
        } finally { dataset.close(); }
    }
}
