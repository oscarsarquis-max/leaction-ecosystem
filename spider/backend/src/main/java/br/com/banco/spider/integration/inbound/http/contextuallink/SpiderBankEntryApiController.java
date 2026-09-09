package br.com.banco.spider.integration.inbound.http.contextuallink;

import br.com.banco.spider.config.ContextualLinkProperties;
import br.com.banco.spider.contextuallink.application.ContextualLinkGatewayService;
import br.com.banco.spider.contextuallink.domain.ContextualLinkSession;
import java.util.LinkedHashMap;
import java.util.Map;
import org.springframework.boot.autoconfigure.condition.ConditionalOnBean;
import org.springframework.context.annotation.Profile;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.server.ResponseStatusException;
import reactor.core.publisher.Mono;

@RestController
@Profile("local-demo")
@ConditionalOnBean(ContextualLinkGatewayService.class)
public class SpiderBankEntryApiController {

  private final ContextualLinkGatewayService gateway;
  private final ContextualLinkProperties properties;

  public SpiderBankEntryApiController(
      ContextualLinkGatewayService gateway, ContextualLinkProperties properties) {
    this.gateway = gateway;
    this.properties = properties;
  }

  @GetMapping("/v1/demo/spiderbank/entry")
  public Mono<Map<String, Object>> entry(@RequestParam("ctx") String ctx) {
    if (ctx == null || ctx.isBlank() || !ctx.startsWith("ctx-")) {
      return Mono.error(new ResponseStatusException(HttpStatus.BAD_REQUEST, "opaque context required"));
    }
    return Mono.justOrEmpty(gateway.find(ctx))
        .switchIfEmpty(Mono.error(new ResponseStatusException(HttpStatus.NOT_FOUND, "unknown context")))
        .map(this::toProjection);
  }

  private Map<String, Object> toProjection(ContextualLinkSession session) {
    Map<String, Object> body = new LinkedHashMap<>();
    body.put("satellite", "SPIDERBANK");
    body.put("mode", "REFERENCE_SATELLITE_DEMO");
    body.put("boundary", Map.of("runtime", "SIMULATED_INFRASTRUCTURE", "integrations", "MOCK_ONLY"));
    body.put("partnerPublicName", properties.getPartnerPublicName());
    body.put("gatewayUrl", session.gatewayUrl());
    body.put("click", session.click());
    body.put("page", session.page());
    body.put("correlation", session.correlation());
    body.put("boundaryFlags", session.boundary());
    body.put("provenance", session.provenance());
    body.put("createdAt", session.click().createdAt().toString());
    body.put(
        "statusLabel",
        switch (session.page().acquisitionStatus()) {
          case CAPTURED -> "CONTEXTO CAPTURADO";
          case ORIGIN_ONLY -> "ORIGEM IDENTIFICADA";
          case UNAVAILABLE -> "CONTEXTO MÍNIMO — ORIGEM NÃO ADQUIRIDA";
          case BLOCKED -> "AQUISIÇÃO BLOQUEADA";
          case FAILED -> "AQUISIÇÃO FALHOU";
        });
    return body;
  }
}
