package br.com.banco.spider.demo.segsense;

import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import br.com.banco.spider.config.SegSenseDemoProperties;
import org.junit.jupiter.api.Test;

class SegSenseDemoApplicationAuthTest {

  @Test
  void emptyConfiguredSecretFailsClosed() {
    SegSenseDemoProperties properties = new SegSenseDemoProperties();
    properties.setCredentialRef("local-demo-segsense");
    properties.setApplicationSecret("");
    SegSenseDemoApplicationAuth auth = new SegSenseDemoApplicationAuth(properties);
    assertFalse(auth.authenticated("local-demo-segsense", "anything"));
  }

  @Test
  void identityIsNotTheSecret() {
    SegSenseDemoProperties properties = new SegSenseDemoProperties();
    properties.setCredentialRef("local-demo-segsense");
    properties.setApplicationSecret("test-only-secret");
    SegSenseDemoApplicationAuth auth = new SegSenseDemoApplicationAuth(properties);
    assertFalse(auth.authenticated("local-demo-segsense", "local-demo-segsense"));
    assertTrue(auth.authenticated("local-demo-segsense", "test-only-secret"));
    assertFalse(auth.authenticated("local-demo-console", "test-only-secret"));
  }
}
