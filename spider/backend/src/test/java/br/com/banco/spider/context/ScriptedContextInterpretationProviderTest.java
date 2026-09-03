package br.com.banco.spider.context;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;

import br.com.banco.spider.context.application.ContextInterpreterPrompt;
import br.com.banco.spider.context.application.port.ContextInterpretationProvider.AllowedIntent;
import br.com.banco.spider.context.application.port.ContextInterpretationProvider.ProviderRequest;
import br.com.banco.spider.context.application.port.ContextInterpretationProvider.ProviderStatus;
import br.com.banco.spider.integration.outbound.ai.ScriptedContextInterpretationProvider;
import java.util.List;
import org.junit.jupiter.api.Test;

class ScriptedContextInterpretationProviderTest {

  private final ScriptedContextInterpretationProvider provider =
      new ScriptedContextInterpretationProvider();

  @Test
  void recognizesCreditAndExtractsOnlyExplicitProposalId() {
    var result =
        provider
            .interpret(request("Verifique a proposta 12345 porque ainda não liberou."))
            .block();
    assertEquals(ProviderStatus.MATCHED, result.status());
    assertEquals("INVESTIGATE_CREDIT_RELEASE", result.intent());
    assertEquals("12345", result.entities().get("proposalId"));
  }

  @Test
  void neverInventsProposalIdWhenItWasNotDeclared() {
    var result =
        provider
            .interpret(request("Minha proposta foi aprovada, mas o crédito não foi liberado."))
            .block();
    assertEquals(ProviderStatus.MATCHED, result.status());
    assertFalse(result.entities().containsKey("proposalId"));
  }

  @Test
  void reportsAmbiguousAndUnsupportedObjectivesWithoutIntent() {
    var ambiguous =
        provider
            .interpret(request("Quero saber o que aconteceu com o cliente João."))
            .block();
    var unsupported =
        provider.interpret(request("Quero comprar passagens para Paris.")).block();
    assertEquals(ProviderStatus.AMBIGUOUS, ambiguous.status());
    assertEquals(3, ambiguous.candidateIntents().size());
    assertEquals(ProviderStatus.UNSUPPORTED_INTENT, unsupported.status());
  }

  @Test
  void fourWorkingCapitalSituationsConvergeWithoutInventingAmount() {
    assertWorkingCapital(
        "Empresa precisa de R$ 50 mil para reforçar o estoque e atender ao aumento das vendas.",
        "INVENTORY",
        "50000");
    assertWorkingCapital(
        "Empresa está com aumento temporário das despesas operacionais e precisa reforçar o caixa.",
        "CASH_FLOW",
        null);
    assertWorkingCapital(
        "Indústria recebeu novos pedidos e precisa adquirir matéria-prima para aumentar a produção.",
        "RAW_MATERIAL",
        null);
    assertWorkingCapital(
        "Supermercado precisa antecipar a compra de mercadorias para um período de maior movimento.",
        "SEASONALITY",
        null);
  }

  private void assertWorkingCapital(String text, String purpose, String amount) {
    var result = provider.interpret(request(text)).block();
    assertEquals(ProviderStatus.MATCHED, result.status());
    assertEquals("SEEK_WORKING_CAPITAL", result.intent());
    assertEquals(purpose, result.entities().get("purpose"));
    assertEquals(amount, result.entities().get("amount"));
  }

  private static ProviderRequest request(String text) {
    return new ProviderRequest(
        text,
        ContextInterpreterPrompt.VERSION,
        "1.0",
        List.of(
            new AllowedIntent(
                "INVESTIGATE_CREDIT_RELEASE",
                "CREDIT",
                "IDENTIFY_BLOCKING_CONDITION",
                List.of("proposalId"),
                List.of("proposalId")),
            new AllowedIntent(
                "SEEK_WORKING_CAPITAL",
                "CREDIT",
                "ASSESS_WORKING_CAPITAL_OPTIONS",
                List.of("amount", "businessSituation", "purpose"),
                List.of("purpose"))));
  }
}
