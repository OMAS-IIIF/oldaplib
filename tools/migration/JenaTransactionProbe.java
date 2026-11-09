import java.nio.file.Files;
import java.nio.file.Path;
import java.util.concurrent.*;
import org.apache.jena.query.*;
import org.apache.jena.tdb2.TDB2Factory;
import org.apache.jena.update.UpdateAction;

/**
 * Synthetic TDB2 transaction acceptance probe, independent of OLDAP services.
 * Input: a new database directory. Output: PASS lines; throws on failed checks.
 * Creates only synthetic triples and closes all transactions, threads and datasets.
 * Dataset transaction state is thread-local; each worker owns its transaction.
 */
public class JenaTransactionProbe {
    private static final String CLAIM = "<urn:jena-probe:claim> <urn:jena-probe:owner>";

    private static void require(boolean condition, String message) {
        if (!condition) throw new AssertionError(message);
    }

    /** Evaluate ASK within the caller's active transaction. */
    private static boolean ask(Dataset dataset, String pattern) {
        try (QueryExecution query = QueryExecutionFactory.create("ASK { " + pattern + " }", dataset)) {
            return query.execAsk();
        }
    }

    /** Insert two synthetic facts, representing a resource and its receipt. */
    private static void insert(Dataset dataset) {
        UpdateAction.parseExecute("INSERT DATA { <urn:jena-probe:resource> <urn:jena-probe:value> 1 . "
                + "<urn:jena-probe:receipt> <urn:jena-probe:value> 1 }", dataset);
    }

    public static void main(String[] args) throws Exception {
        if (args.length != 1 || Files.exists(Path.of(args[0]))) {
            throw new IllegalArgumentException("Supply exactly one new database directory.");
        }
        Dataset dataset = TDB2Factory.connectDataset(args[0]);
        ExecutorService readers = Executors.newSingleThreadExecutor();
        try {
            dataset.begin(ReadWrite.WRITE);
            try {
                insert(dataset);
                require(ask(dataset, "<urn:jena-probe:resource> ?p ?o"), "Read own write failed");
                Future<Boolean> external = readers.submit(() -> {
                    dataset.begin(ReadWrite.READ);
                    try { return ask(dataset, "?s ?p ?o"); }
                    finally { dataset.end(); }
                });
                require(!external.get(10, TimeUnit.SECONDS), "Reader saw uncommitted facts");
                dataset.abort();
            } finally { dataset.end(); }
            dataset.begin(ReadWrite.READ);
            try { require(!ask(dataset, "?s ?p ?o"), "Rollback left resource/receipt facts"); }
            finally { dataset.end(); }
            System.out.println("PASS read-own-writes, concurrent-reader isolation, full rollback");

            dataset.begin(ReadWrite.WRITE);
            try { insert(dataset); dataset.commit(); }
            finally { dataset.end(); }
            dataset.begin(ReadWrite.READ);
            try {
                require(ask(dataset, "<urn:jena-probe:resource> ?p ?o . <urn:jena-probe:receipt> ?p2 ?o2"),
                        "Commit did not retain both facts");
            } finally { dataset.end(); }
            System.out.println("PASS resource-and-receipt commit visibility");

            ExecutorService writers = Executors.newFixedThreadPool(2);
            CountDownLatch start = new CountDownLatch(1);
            try {
                Future<Boolean> first = writers.submit(() -> claim(dataset, start, "first"));
                Future<Boolean> second = writers.submit(() -> claim(dataset, start, "second"));
                start.countDown();
                int winners = (first.get(15, TimeUnit.SECONDS) ? 1 : 0)
                        + (second.get(15, TimeUnit.SECONDS) ? 1 : 0);
                require(winners == 1, "Conflicting transactions both claimed the same resource");
            } finally { writers.shutdownNow(); }
            System.out.println("PASS concurrent read-check-write claims: exactly one winner");
        } finally {
            readers.shutdownNow();
            dataset.close();
        }
        Dataset reopened = TDB2Factory.connectDataset(args[0]);
        try {
            reopened.begin(ReadWrite.READ);
            try { require(ask(reopened, "<urn:jena-probe:receipt> ?p ?o"), "Reopen lost committed receipt"); }
            finally { reopened.end(); }
        } finally { reopened.close(); }
        System.out.println("PASS dataset close/reopen retains committed data (not a crash test)");
    }

    /** Compete for one claim with the read and write inside a single transaction. */
    private static boolean claim(Dataset dataset, CountDownLatch start, String owner) throws Exception {
        start.await();
        dataset.begin(ReadWrite.WRITE);
        try {
            if (ask(dataset, CLAIM + " ?owner")) {
                dataset.abort();
                return false;
            }
            UpdateAction.parseExecute("INSERT DATA { " + CLAIM + " \"" + owner + "\" }", dataset);
            dataset.commit();
            return true;
        } finally { dataset.end(); }
    }
}
