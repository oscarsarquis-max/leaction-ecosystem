package br.com.banco.spider.application.canonical;

import br.com.banco.spider.application.security.AuthorizationDecision;
import br.com.banco.spider.security.integrity.IntegrityKeyRotationService;
import br.com.banco.spider.security.integrity.IntegrityProfileCatalogPort;
import br.com.banco.spider.security.integrity.IntegrityProfileDefinition;
import java.util.ArrayList;
import java.util.List;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;
import reactor.core.publisher.Mono;

/** Health operacional de perfis — deny-by-default, sem Controller HTTP. */
@Service
public class IntegrityProfileHealthCheckUseCase {

  private static final Logger log = LoggerFactory.getLogger(IntegrityProfileHealthCheckUseCase.class);

  private final CallbackOpsAuthorizationPort authorization;
  private final IntegrityProfileCatalogPort catalog;
  private final IntegrityKeyRotationService rotation;

  public IntegrityProfileHealthCheckUseCase(
      CallbackOpsAuthorizationPort authorization,
      IntegrityProfileCatalogPort catalog,
      IntegrityKeyRotationService rotation) {
    this.authorization = authorization;
    this.catalog = catalog;
    this.rotation = rotation;
  }

  public record Command(String actorRef, String reasonCode, List<String> profileRefs) {}

  public record ProfileHealth(String profileRef, String activeVersion, String reasonCode) {}

  public record Outcome(AuthorizationDecision decision, List<ProfileHealth> profiles) {}

  public Mono<Outcome> execute(Command command) {
    return authorization
        .authorize("integrity.health", command.actorRef())
        .map(
            decision -> {
              if (decision != AuthorizationDecision.PERMIT) {
                log.info("event=integrity_health_denied reasonCode=DENIED");
                return new Outcome(decision, List.of());
              }
              List<ProfileHealth> list = new ArrayList<>();
              for (String ref :
                  command.profileRefs() == null ? List.<String>of() : command.profileRefs()) {
                IntegrityProfileDefinition p = catalog.findByExactRef(ref).orElse(null);
                if (p == null) {
                  list.add(new ProfileHealth(ref, null, "PROFILE_NOT_FOUND"));
                } else if (p.status().name().equals("REVOKED")) {
                  list.add(new ProfileHealth(ref, null, "REVOKED"));
                } else {
                  var s = rotation.summarize(p);
                  list.add(new ProfileHealth(ref, s.activeVersion(), "OK"));
                }
              }
              log.info("event=integrity_health_ok count={}", list.size());
              return new Outcome(AuthorizationDecision.PERMIT, list);
            });
  }
}
