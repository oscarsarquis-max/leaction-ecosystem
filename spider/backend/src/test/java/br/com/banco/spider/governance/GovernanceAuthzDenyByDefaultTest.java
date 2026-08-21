package br.com.banco.spider.governance;

import static org.junit.jupiter.api.Assertions.assertEquals;

import br.com.banco.spider.application.security.AuthorizationDecision;
import java.util.List;
import org.junit.jupiter.api.Test;
import reactor.core.publisher.Mono;
import reactor.test.StepVerifier;

class GovernanceAuthzDenyByDefaultTest {

  @Test
  void defaultPortDenies() {
    GovernanceAuthorizationPort port =
        new GovernanceAuthorizationDefaultsConfig().denyAllGovernanceAuthorization();
    StepVerifier.create(port.authorize("governance.bundle.publish", "actor"))
        .assertNext(d -> assertEquals(AuthorizationDecision.DENY, d))
        .verifyComplete();
  }
}
