package br.com.banco.spider.application.canonical;

import static org.junit.jupiter.api.Assertions.assertEquals;

import br.com.banco.spider.application.security.AuthorizationDecision;
import br.com.banco.spider.security.integrity.ConfiguredIntegrityProfileCatalog;
import br.com.banco.spider.security.integrity.IntegrityKeyRotationService;
import java.util.List;
import org.junit.jupiter.api.Test;
import reactor.core.publisher.Mono;
import reactor.test.StepVerifier;

class IntegrityOpsDenyByDefaultTest {

  @Test
  void healthDeniedByDefault() {
    IntegrityProfileHealthCheckUseCase useCase =
        new IntegrityProfileHealthCheckUseCase(
            (op, actor) -> Mono.just(AuthorizationDecision.DENY),
            new ConfiguredIntegrityProfileCatalog(List.of()),
            new IntegrityKeyRotationService());
    StepVerifier.create(
            useCase.execute(
                new IntegrityProfileHealthCheckUseCase.Command("actor", "OPS", List.of("p@1"))))
        .assertNext(o -> assertEquals(AuthorizationDecision.DENY, o.decision()))
        .verifyComplete();
  }
}
