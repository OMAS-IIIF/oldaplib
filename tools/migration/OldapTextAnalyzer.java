import java.io.IOException;
import java.text.Normalizer;
import org.apache.lucene.analysis.Analyzer;
import org.apache.lucene.analysis.LowerCaseFilter;
import org.apache.lucene.analysis.TokenFilter;
import org.apache.lucene.analysis.TokenStream;
import org.apache.lucene.analysis.standard.StandardTokenizer;
import org.apache.lucene.analysis.miscellaneous.ASCIIFoldingFilter;
import org.apache.lucene.analysis.tokenattributes.CharTermAttribute;

/** Language-neutral archive search: case, canonical Unicode and Latin accents.
 *
 * Indexed text and query terms use the same transformation. No stemming,
 * compound splitting or stop-word removal is applied. Positions and offsets
 * retain the tokenizer's values so phrase matching stays positional. Only
 * index tokens change; the authoritative RDF literal is never rewritten.
 */
final class OldapTextAnalyzer extends Analyzer {
    private TokenStream folded(TokenStream input) {
        // Compose combining marks before ASCII folding, so precomposed and
        // decomposed umlauts share one token. Preserve one token per position.
        return new ASCIIFoldingFilter(new CanonicalFilter(new LowerCaseFilter(input)), false);
    }

    @Override protected TokenStreamComponents createComponents(String fieldName) {
        StandardTokenizer tokenizer = new StandardTokenizer();
        return new TokenStreamComponents(tokenizer, folded(tokenizer));
    }

    @Override protected TokenStream normalize(String fieldName, TokenStream input) {
        // Lucene normalizes wildcard/prefix terms without normal tokenization.
        // Apply exactly the same one-token folding here, including ß -> ss.
        return folded(input);
    }

    /** Canonically compose each token without changing positions or offsets. */
    private static final class CanonicalFilter extends TokenFilter {
        private final CharTermAttribute term = addAttribute(CharTermAttribute.class);
        CanonicalFilter(TokenStream input) { super(input); }
        @Override public boolean incrementToken() throws IOException {
            if (!input.incrementToken()) return false;
            String normalized = Normalizer.normalize(term.toString(), Normalizer.Form.NFC);
            term.setEmpty().append(normalized);
            return true;
        }
    }
}
