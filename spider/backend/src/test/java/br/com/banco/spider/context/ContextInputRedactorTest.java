package br.com.banco.spider.context;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import br.com.banco.spider.context.application.ContextInputRedactor;
import org.junit.jupiter.api.Test;

class ContextInputRedactorTest {

  private final ContextInputRedactor redactor = new ContextInputRedactor(2000);

  @Test
  void removesCredentialsTokensAndPersonalIdentifiersBeforeProvider() {
    var result =
        redactor.redact(
            "Verifique proposta 12345 token=segredo Bearer abc.def "
                + "CPF 123.456.789-00 e email pessoa@example.com");

    assertTrue(result.safeObjective().contains("proposta 12345"));
    assertFalse(result.safeObjective().contains("segredo"));
    assertFalse(result.safeObjective().contains("abc.def"));
    assertFalse(result.safeObjective().contains("123.456.789-00"));
    assertFalse(result.safeObjective().contains("pessoa@example.com"));
    assertEquals(4, result.redactedFieldsCount());
  }

  @Test
  void preservesBusinessObjectiveWithoutInventingOrChangingEntities() {
    String objective = "Verifique a proposta 12345 porque ainda não liberou.";
    var result = redactor.redact(objective);
    assertEquals(objective, result.safeObjective());
    assertEquals(0, result.redactedFieldsCount());
  }
}
