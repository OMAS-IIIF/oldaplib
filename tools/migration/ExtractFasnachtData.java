import java.nio.file.*;
import java.io.OutputStream;
import org.apache.jena.query.*;
import org.apache.jena.riot.*;
import org.apache.jena.graph.NodeFactory;

/** Extract only instance RDF for a fresh-model rehearsal; never import source accounts/model. */
public class ExtractFasnachtData {
    public static void main(String[] args) throws Exception {
        if (args.length != 2) throw new IllegalArgumentException("input converted.trig, new output data.trig");
        Dataset source = DatasetFactory.create();
        Dataset target = DatasetFactory.create();
        try {
            RDFDataMgr.read(source, args[0]);
            var graph = NodeFactory.createURI("http://fasnacht.digital/ns/data");
            var quads = source.asDatasetGraph().find(graph, null, null, null);
            long count = 0;
            while (quads.hasNext()) { target.asDatasetGraph().add(quads.next()); count++; }
            if (count == 0) throw new IllegalArgumentException("Expected Fasnacht data graph is empty or absent");
            try (OutputStream out = Files.newOutputStream(Path.of(args[1]), StandardOpenOption.CREATE_NEW)) {
                RDFDataMgr.write(out, target, Lang.TRIG);
            }
            System.out.println("Extracted instance quads: " + count);
        } finally {
            target.close();
            source.close();
        }
    }
}
