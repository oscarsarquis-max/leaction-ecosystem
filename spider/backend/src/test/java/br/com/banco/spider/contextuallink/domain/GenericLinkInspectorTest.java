package br.com.banco.spider.contextuallink.domain;

import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.util.Set;
import org.junit.jupiter.api.Test;

class GenericLinkInspectorTest {

  @Test
  void genericGoHasNoContextualQuery() {
    String href = "http://127.0.0.1:8080/go";
    assertFalse(GenericLinkInspector.hasContextualQuery(href));
    assertTrue(GenericLinkInspector.isGenericGatewayPath(href, Set.of(href)));
  }

  @Test
  void rejectsEmbeddedIntent() {
    assertTrue(GenericLinkInspector.hasContextualQuery("http://127.0.0.1:8080/go?intent=credit"));
    assertFalse(
        GenericLinkInspector.isGenericGatewayPath(
            "http://127.0.0.1:8080/go?intent=credit", Set.of("http://127.0.0.1:8080/go")));
  }
}
