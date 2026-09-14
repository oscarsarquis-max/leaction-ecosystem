package br.com.segsense.application.demo;

import br.com.segsense.domain.demo.DemoProtectionException;
import java.util.regex.Pattern;

public final class DemoPersonalDataGuard {

  private static final Pattern EMAIL = Pattern.compile("[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}");
  private static final Pattern CPF = Pattern.compile("\\b\\d{3}\\.?\\d{3}\\.?\\d{3}-?\\d{2}\\b");
  private static final Pattern PHONE = Pattern.compile("\\b(?:\\+?55\\s?)?(?:\\(?\\d{2}\\)?\\s?)?9?\\d{4}-?\\d{4}\\b");

  private DemoPersonalDataGuard() {}

  public static void rejectObviousPersonalData(String text) {
    if (text == null || text.isBlank()) {
      return;
    }
    if (EMAIL.matcher(text).find() || CPF.matcher(text).find() || PHONE.matcher(text).find()) {
      throw new DemoProtectionException(
          "PERSONAL_DATA_NOT_ALLOWED",
          400,
          "Remova dados pessoais óbvios (e-mail, CPF ou telefone). Esta detecção não é perfeita.");
    }
  }
}
