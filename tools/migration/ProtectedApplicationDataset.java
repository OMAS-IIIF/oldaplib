import java.util.*;
import org.apache.jena.graph.*;
import org.apache.jena.query.*;
import org.apache.jena.riot.system.PrefixMap;
import org.apache.jena.sparql.core.*;
import org.apache.jena.util.iterator.WrappedIterator;

/**
 * Experimental application view over the SAME transactional storage as receipts.
 * Reads cannot see the reserved graph; explicit writes to it are rejected.
 * Bulk operations affect application graphs only. Transaction ownership stays
 * with the caller. This protects metadata, not OLDAP per-resource permissions.
 *
 * Deliberately extends DatasetGraphBase, not a transparent wrapper: a query
 * optimizer must not unwrap this boundary and access the backing TDB2 dataset.
 * All Graph objects are views back through this boundary, never backing graphs.
 */
public final class ProtectedApplicationDataset extends DatasetGraphBase {
    private final DatasetGraph storage;
    private final Node reserved;

    public ProtectedApplicationDataset(DatasetGraph storage, String receiptGraph) {
        this.storage = storage;
        this.reserved = NodeFactory.createURI(receiptGraph);
    }

    private void writable(Node graph) {
        if (reserved.equals(graph)) throw new IllegalArgumentException("Reserved transaction metadata graph");
    }

    @Override public Graph getDefaultGraph() { return GraphView.createDefaultGraph(this); }
    @Override public Graph getUnionGraph() { return GraphView.createUnionGraph(this); }
    @Override public Graph getGraph(Node graph) {
        if (Quad.isDefaultGraph(graph)) return getDefaultGraph();
        if (Quad.isUnionGraph(graph)) return getUnionGraph();
        return GraphView.createNamedGraph(this, graph);
    }
    @Override public Iterator<Node> listGraphNodes() {
        return WrappedIterator.create(storage.listGraphNodes()).filterDrop(reserved::equals);
    }
    @Override public Iterator<Quad> find(Node g, Node s, Node p, Node o) {
        if (reserved.equals(g)) return Collections.emptyIterator();
        if (Quad.isUnionGraph(g))
            return org.apache.jena.atlas.iterator.Iter.distinct(
                WrappedIterator.create(findNG(Node.ANY, s, p, o)).mapWith(q -> Quad.create(g, q.asTriple())));
        return WrappedIterator.create(storage.find(g, s, p, o)).filterDrop(q -> reserved.equals(q.getGraph()));
    }
    @Override public Iterator<Quad> findNG(Node g, Node s, Node p, Node o) {
        if (reserved.equals(g)) return Collections.emptyIterator();
        if (Quad.isUnionGraph(g)) return find(g, s, p, o);
        return WrappedIterator.create(storage.findNG(g, s, p, o)).filterDrop(q -> reserved.equals(q.getGraph()));
    }
    @Override public void add(Node g, Node s, Node p, Node o) {
        writable(g);
        storage.add(g, s, p, o);
    }
    @Override public void add(Quad quad) {
        add(quad.getGraph(), quad.getSubject(), quad.getPredicate(), quad.getObject());
    }
    @Override public void delete(Quad quad) {
        delete(quad.getGraph(), quad.getSubject(), quad.getPredicate(), quad.getObject());
    }
    @Override public void delete(Node g, Node s, Node p, Node o) {
        writable(g);
        storage.delete(g, s, p, o);
    }
    @Override public void deleteAny(Node g, Node s, Node p, Node o) {
        writable(g);
        // The base implementation finds through this view before deleting,
        // so wildcard deletion cannot touch hidden metadata.
        super.deleteAny(g, s, p, o);
    }
    @Override public void addGraph(Node graph, Graph contents) {
        writable(graph);
        removeGraph(graph);
        var triples = contents.find();
        try { triples.forEachRemaining(t -> add(graph, t.getSubject(), t.getPredicate(), t.getObject())); }
        finally { triples.close(); }
    }
    @Override public void removeGraph(Node graph) {
        writable(graph);
        storage.removeGraph(graph);
    }
    @Override public PrefixMap prefixes() { return storage.prefixes(); }

    // Delegation preserves atomicity: receipt writes use storage directly,
    // application statements use this view, both in the same TDB2 transaction.
    @Override public void begin(TxnType type) { storage.begin(type); }
    @Override public boolean promote(Promote mode) { return storage.promote(mode); }
    @Override public void commit() { storage.commit(); }
    @Override public void abort() { storage.abort(); }
    @Override public void end() { storage.end(); }
    @Override public ReadWrite transactionMode() { return storage.transactionMode(); }
    @Override public TxnType transactionType() { return storage.transactionType(); }
    @Override public boolean isInTransaction() { return storage.isInTransaction(); }
    @Override public boolean supportsTransactions() { return storage.supportsTransactions(); }
    @Override public boolean supportsTransactionAbort() { return storage.supportsTransactionAbort(); }
    @Override public void close() { /* Storage lifecycle belongs to the server owner. */ }
}
