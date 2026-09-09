package br.com.banco.spider.context.domain;

import java.text.Normalizer;
import java.util.Locale;

/**
 * Evidência lexical de quebra de safra. Nunca lê o link, a campanha ou um código do SpiderBank.
 */
public final class CropFailureEvidence {

  private CropFailureEvidence() {}

  public static boolean in(String... texts) {
    String normalized = normalize(join(texts));
    if (normalized.isBlank()) {
      return false;
    }
    return normalized.contains("quebra de safra")
        || (normalized.contains("quebra") && normalized.contains("safra"))
        || (normalized.contains("perdi") && normalized.contains("safra"))
        || (normalized.contains("perda") && normalized.contains("safra"))
        || normalized.contains("perda de producao");
  }

  public static String normalize(String text) {
    if (text == null || text.isBlank()) {
      return "";
    }
    return Normalizer.normalize(text, Normalizer.Form.NFD)
        .replaceAll("\\p{M}+", "")
        .toLowerCase(Locale.ROOT);
  }

  private static String join(String... texts) {
    if (texts == null || texts.length == 0) {
      return "";
    }
    StringBuilder builder = new StringBuilder();
    for (String text : texts) {
      if (text != null && !text.isBlank()) {
        if (builder.length() > 0) {
          builder.append(' ');
        }
        builder.append(text);
      }
    }
    return builder.toString();
  }
}
