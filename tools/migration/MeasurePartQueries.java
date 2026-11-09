import java.nio.file.*;
import java.io.*;
import java.security.MessageDigest;
import java.util.HexFormat;
import org.apache.jena.query.*;
import org.apache.jena.tdb2.TDB2Factory;

/** Read-only query-shape measurements on a disposable copy of a closed fixture. */
public class MeasurePartQueries {
    public static void main(String[] args) throws Exception {
        Dataset dataset = TDB2Factory.connectDataset(args[0]);
        try {
            dataset.begin(ReadWrite.READ);
            for (int i=1; i<args.length; i++) {
                String query = Files.readString(Path.of(args[i]));
                for (int repeat=0; repeat<3; repeat++) {
                    long start = System.nanoTime();
                    ByteArrayOutputStream bytes = new ByteArrayOutputStream();
                    try (QueryExecution execution = QueryExecutionFactory.create(query, dataset)) {
                        ResultSetFormatter.outputAsJSON(bytes, execution.execSelect());
                    }
                    double ms = (System.nanoTime()-start)/1_000_000.0;
                    String hash = HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(bytes.toByteArray()));
                    System.out.println(Path.of(args[i]).getFileName()+"\t"+repeat+"\t"+ms+"\t"+hash);
                }
            }
        } finally { dataset.end(); dataset.close(); }
    }
}
