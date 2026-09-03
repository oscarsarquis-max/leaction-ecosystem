package br.com.banco.spider.context;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import br.com.banco.spider.context.application.ContextInterpreterPrompt;
import br.com.banco.spider.context.application.port.ContextInterpretationProvider.AllowedIntent;
import br.com.banco.spider.context.application.port.ContextInterpretationProvider.ProviderRequest;
import br.com.banco.spider.context.application.port.ContextInterpretationProvider.ProviderStatus;
import br.com.banco.spider.context.application.port.InvalidContextInterpretationResponseException;
import br.com.banco.spider.integration.outbound.ai.BedrockContextInterpretationProvider;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.util.List;
import java.util.concurrent.CompletableFuture;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import software.amazon.awssdk.core.SdkBytes;
import software.amazon.awssdk.services.bedrockruntime.BedrockRuntimeAsyncClient;
import software.amazon.awssdk.services.bedrockruntime.model.InvokeModelRequest;
import software.amazon.awssdk.services.bedrockruntime.model.InvokeModelResponse;

class BedrockContextInterpretationProviderTest {

  @Test
  void parsesStrictAnthropicStructuredOutputAndUsage() {
    BedrockRuntimeAsyncClient client = mock(BedrockRuntimeAsyncClient.class);
    when(client.invokeModel(any(InvokeModelRequest.class)))
        .thenReturn(
            CompletableFuture.completedFuture(
                response(
                    """
                    {"content":[{"type":"text","text":"{\\"status\\":\\"MATCHED\\",\\"intent\\":\\"INVESTIGATE_CREDIT_RELEASE\\",\\"entities\\":{\\"proposalId\\":\\"12345\\"},\\"candidateIntents\\":[],\\"confidence\\":0.94}"}],"usage":{"input_tokens":120,"output_tokens":35}}
                    """)));
    var provider = provider(client);
    var result = provider.interpret(request()).block();

    assertEquals(ProviderStatus.MATCHED, result.status());
    assertEquals("12345", result.entities().get("proposalId"));
    assertEquals(155, result.usage().totalTokens());

    ArgumentCaptor<InvokeModelRequest> captor =
        ArgumentCaptor.forClass(InvokeModelRequest.class);
    verify(client).invokeModel(captor.capture());
    String requestJson = captor.getValue().body().asUtf8String();
    assertFalse(requestJson.contains("routeRef"));
    assertFalse(requestJson.contains("capabilityRef"));
    assertFalse(requestJson.contains("endpointRef"));
    assertFalse(requestJson.contains("\"executionPlan\""));
    assertFalse(requestJson.contains("\"eligibleRoutes\""));
  }

  @Test
  void rejectsFreeTextOrMarkdownInsteadOfStructuredObject() {
    BedrockRuntimeAsyncClient client = mock(BedrockRuntimeAsyncClient.class);
    when(client.invokeModel(any(InvokeModelRequest.class)))
        .thenReturn(
            CompletableFuture.completedFuture(
                response(
                    """
                    {"content":[{"type":"text","text":"```json\\n{\\"status\\":\\"MATCHED\\"}\\n```"}],"usage":{}}
                    """)));
    assertThrows(
        InvalidContextInterpretationResponseException.class,
        () -> provider(client).interpret(request()).block());
  }

  private static BedrockContextInterpretationProvider provider(
      BedrockRuntimeAsyncClient client) {
    return new BedrockContextInterpretationProvider(
        client,
        new ObjectMapper(),
        new ContextInterpreterPrompt(
            ContextInterpreterPrompt.VERSION,
            "Return structured JSON. Never choose routes or execute actions."),
        "anthropic.test-model-v1");
  }

  private static ProviderRequest request() {
    return new ProviderRequest(
        "Verifique a proposta 12345.",
        ContextInterpreterPrompt.VERSION,
        "1.0",
        List.of(
            new AllowedIntent(
                "INVESTIGATE_CREDIT_RELEASE",
                "CREDIT",
                "IDENTIFY_BLOCKING_CONDITION",
                List.of("proposalId"),
                List.of("proposalId"))));
  }

  private static InvokeModelResponse response(String json) {
    return InvokeModelResponse.builder().body(SdkBytes.fromUtf8String(json)).build();
  }
}
