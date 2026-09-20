package br.com.segsense.application.demo;

import static org.junit.jupiter.api.Assertions.assertEquals;

import org.junit.jupiter.api.Test;

class DemoIntentionClassifierTest {

  @Test
  void classifiesHomeProtectionWithoutDefaultingBlankText() {
    assertEquals(
        DemoIntentionClassifier.SIMULATE_HOME_QUOTE,
        DemoIntentionClassifier.code("Quero contratar um seguro residencial"));
    assertEquals(DemoIntentionClassifier.UNRECOGNIZED, DemoIntentionClassifier.code(""));
    assertEquals(DemoIntentionClassifier.UNRECOGNIZED, DemoIntentionClassifier.code("quero um desconto"));
    assertEquals(DemoIntentionClassifier.EFFECTIVE_CONTRACT, DemoIntentionClassifier.code("quero pagar agora"));
    assertEquals(
        DemoIntentionClassifier.UNDERSTAND,
        DemoIntentionClassifier.code("entender opções ilustrativas de proteção"));
    assertEquals(
        DemoIntentionClassifier.UNDERSTAND,
        DemoIntentionClassifier.code("Quero entender opções de proteção para perda de produção"));
  }
}
