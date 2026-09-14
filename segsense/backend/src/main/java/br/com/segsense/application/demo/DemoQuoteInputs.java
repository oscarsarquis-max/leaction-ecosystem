package br.com.segsense.application.demo;

import br.com.segsense.domain.demo.DemoProtectionException;
import java.util.Set;

public final class DemoQuoteInputs {

  public static final long MIN_CENTS = 5_000_000L;
  public static final long MAX_CENTS = 200_000_000L;
  public static final Set<String> DWELLINGS = Set.of("APARTMENT", "HOUSE");

  private DemoQuoteInputs() {}

  public static void validateOptional(String dwellingType, String insuredAmountCents, String coverPeriodMonths) {
    if (has(dwellingType) && !DWELLINGS.contains(dwellingType)) {
      throw new DemoProtectionException(
          "VALIDATION_ERROR", 400, "O tipo de imóvel desta simulação precisa ser apartamento ou casa.");
    }
    if (has(insuredAmountCents)) {
      long cents;
      try {
        cents = Long.parseLong(insuredAmountCents);
      } catch (NumberFormatException ignored) {
        throw new DemoProtectionException(
            "VALIDATION_ERROR", 400, "O valor de proteção desta simulação precisa ser um número inteiro em centavos.");
      }
      if (cents < MIN_CENTS || cents > MAX_CENTS) {
        throw new DemoProtectionException(
            "VALIDATION_ERROR",
            400,
            "O valor de proteção desta simulação precisa ficar entre R$ 50.000 e R$ 2.000.000.");
      }
    }
    if (has(coverPeriodMonths) && !"12".equals(coverPeriodMonths)) {
      throw new DemoProtectionException(
          "VALIDATION_ERROR", 400, "Nesta fatia o período da simulação é de 12 meses.");
    }
  }

  private static boolean has(String value) {
    return value != null && !value.isBlank();
  }
}
