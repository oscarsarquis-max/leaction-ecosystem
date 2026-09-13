package br.com.segsense.domain.demonstration;

import br.com.segsense.domain.catalog.CatalogValidationException;
import java.util.regex.Pattern;

public final class DemonstrationText {

  private static final Pattern UNSAFE =
      Pattern.compile("(?i)<|javascript:|data:|vbscript:|on\\w+\\s*=|</|iframe|script");
  private static final Pattern PERSONAL =
      Pattern.compile(
          "(?i)(^|[^a-zà-ú])(cpf|cnpj|e-?mail|telefone|phone|celular|nome|firstname|lastname|endere[cç]o|address|geolocation|latitude|longitude|nascimento|userid|birthdate)([^a-zà-ú]|$)");

  private DemonstrationText() {}

  public static String required(String raw, String field, int min, int max) {
    if (raw == null) {
      throw new CatalogValidationException(field + " é obrigatório.");
    }
    String value = raw.trim();
    if (value.length() < min || value.length() > max) {
      throw new CatalogValidationException(
          field + " deve ter entre " + min + " e " + max + " caracteres.");
    }
    rejectUnsafe(value, field);
    rejectPersonal(value, field);
    return value;
  }

  public static void rejectUnsafe(String value, String field) {
    if (UNSAFE.matcher(value).find()) {
      throw new CatalogValidationException(
          field + " não pode conter HTML, script, iframe ou marcação insegura.");
    }
  }

  public static void rejectPersonal(String value, String field) {
    if (PERSONAL.matcher(value).find()) {
      throw new CatalogValidationException(
          field + " não pode identificar dado pessoal nesta etapa.");
    }
  }
}
