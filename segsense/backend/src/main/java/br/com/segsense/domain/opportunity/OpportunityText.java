package br.com.segsense.domain.opportunity;

import br.com.segsense.domain.catalog.CatalogValidationException;
import java.util.regex.Pattern;

public final class OpportunityText {

  private static final Pattern HTML_OR_SCRIPT =
      Pattern.compile("(?i)<|javascript:|on\\w+\\s*=");
  private static final Pattern PERSONAL_WORD =
      Pattern.compile(
          "(?i)(^|[^a-zà-ú])(cpf|cnpj|e-?mail|telefone|phone|celular|nome|firstname|lastname|endere[cç]o|address|geolocation|latitude|longitude|nascimento|userid|birthdate)([^a-zà-ú]|$)");

  private OpportunityText() {}

  public static String requiredLength(String raw, String field, int min, int max) {
    if (raw == null) {
      throw new CatalogValidationException(field + " é obrigatório.");
    }
    String value = raw.trim();
    if (value.length() < min || value.length() > max) {
      throw new CatalogValidationException(field + " deve ter entre " + min + " e " + max + " caracteres.");
    }
    rejectUnsafe(value, field);
    return value;
  }

  public static void rejectUnsafe(String value, String field) {
    if (HTML_OR_SCRIPT.matcher(value).find()) {
      throw new CatalogValidationException(field + " não pode conter HTML, script ou marcação insegura.");
    }
  }

  public static void rejectPersonalIdentifier(String raw, String field) {
    if (PERSONAL_WORD.matcher(raw.trim()).find()) {
      throw new CatalogValidationException(
          field + " não pode identificar dado pessoal (somente NON_PERSONAL nesta etapa).");
    }
  }
}
