package br.com.banco.spider.context;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;

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

  private static ProviderRequest request(String text) {
    return new ProviderRequest(
        text,
        "CTX-INTERPRETER-1.0",
        "1.0",
        List.of(
            new AllowedIntent(
                "INVESTIGATE_CREDIT_RELEASE",
                "CREDIT",
                "IDENTIFY_BLOCKING_CONDITION",
                List.of("proposalId"))));
  }
}
