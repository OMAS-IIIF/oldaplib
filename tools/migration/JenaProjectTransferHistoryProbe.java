import org.apache.jena.atlas.json.*;
import org.apache.jena.query.*;
import org.apache.jena.riot.*;

/** Offline regression for history transfer, legacy dumps and graph-scope enforcement. */
public final class JenaProjectTransferHistoryProbe {
    private static final String ACTOR = "urn:test:root";
    private static final String PREFIXES = """
        PREFIX oldap: <http://oldap.org/base#>
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        PREFIX test: <urn:test:>
        """;

    private static Dataset dataset() {
        Dataset data = DatasetFactory.create();
        RDFParser.fromString(PREFIXES + """
            oldap:admin {
                test:root oldap:inProject oldap:SystemProject .
                test:grant rdf:reifies <<( test:root oldap:inProject oldap:SystemProject )>> ;
                    oldap:hasAdminPermission oldap:ADMIN_OLDAP .
                test:project a oldap:Project ; oldap:projectShortName "test" ; oldap:namespaceIri test: .
            }
            """, Lang.TRIG).parse(data);
        return data;
    }

    private static String request(String parts, String trig) {
        JsonObject value = JSON.parse("{\"project\":\"test\",\"parts\":" + parts + "}");
        if (trig != null) value.put("trig", trig);
        return value.toString();
    }

    private static void check(boolean condition, String message) {
        if (!condition) throw new AssertionError(message);
        System.out.println("PASS " + message);
    }

    public static void main(String[] args) {
        Dataset source = dataset(), target = dataset();
        try {
            RDFParser.fromString(PREFIXES + """
                test:data { test:item test:title "current" . }
                test:history {
                    test:h1 a oldap:PropertyHistory ; oldap:historyResource test:item ;
                        oldap:historyProperty test:title ; oldap:historyUser test:root ;
                        oldap:historyValue "früher"@de, 42, test:reference ;
                        oldap:historyDatingSnapshot "<urn:dating> <urn:start> 1900 ." .
                    test:empty a oldap:PropertyHistory ; oldap:historyResource test:item .
                }
                """, Lang.TRIG).parse(source);
            String parts = "[\"data\",\"history\"]";
            String exported = JenaProjectTransfer.exportGraphs(source, ACTOR, request(parts, null));
            JenaProjectTransfer.importGraphs(target, ACTOR, request(parts, exported));
            for (String graph : new String[]{"data", "history"}) {
                check(source.getNamedModel("urn:test:" + graph).isIsomorphicWith(
                    target.getNamedModel("urn:test:" + graph)), graph + " round trip preserves RDF values");
            }
            Dataset legacy = dataset();
            try {
                String dataOnly = "[\"data\"]";
                JenaProjectTransfer.importGraphs(legacy, ACTOR, request(dataOnly,
                    JenaProjectTransfer.exportGraphs(source, ACTOR, request(dataOnly, null))));
                check(legacy.getNamedModel("urn:test:history").isEmpty(), "legacy data-only dump remains supported");
            } finally { legacy.close(); }
            long before = target.getNamedModel("urn:test:history").size();
            try {
                JenaProjectTransfer.importGraphs(target, ACTOR, request(parts,
                    "<urn:test:history> { <urn:new> <urn:p> 1 } <urn:other:history> { <urn:new> <urn:p> 2 }"));
                throw new AssertionError("foreign graph accepted");
            } catch (JenaSessionEngine.Refusal expected) {
                check(target.getNamedModel("urn:test:history").size() == before,
                    "out-of-scope import refuses before modifying selected graphs");
            }
            try {
                JenaProjectTransfer.exportGraphs(source, "urn:test:reader", request(parts, null));
                throw new AssertionError("non-root export accepted");
            } catch (JenaSessionEngine.Refusal expected) {
                System.out.println("PASS raw history transfer requires root permission");
            }
        } finally { source.close(); target.close(); }
    }
}
