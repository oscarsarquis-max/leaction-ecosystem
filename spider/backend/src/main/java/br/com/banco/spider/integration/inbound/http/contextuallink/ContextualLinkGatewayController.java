package br.com.banco.spider.integration.inbound.http.contextuallink;

import br.com.banco.spider.contextuallink.application.ContextualLinkGatewayService;
import org.springframework.boot.autoconfigure.condition.ConditionalOnBean;
import org.springframework.context.annotation.Profile;
import org.springframework.http.HttpStatus;
import org.springframework.http.server.reactive.ServerHttpRequest;
import org.springframework.http.server.reactive.ServerHttpResponse;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;
import reactor.core.publisher.Mono;

@RestController
@Profile("local-demo")
@ConditionalOnBean(ContextualLinkGatewayService.class)
public class ContextualLinkGatewayController {

  private final ContextualLinkGatewayService gateway;

  public ContextualLinkGatewayController(ContextualLinkGatewayService gateway) {
    this.gateway = gateway;
  }

  @GetMapping("/go")
  public Mono<Void> go(ServerHttpRequest request, ServerHttpResponse response) {
    String referer = request.getHeaders().getFirst("Referer");
    if (referer == null) {
      referer = request.getHeaders().getFirst("Referrer");
    }
    return gateway
        .handleClick(referer)
        .flatMap(
            session -> {
              response.setStatusCode(HttpStatus.FOUND);
              response.getHeaders().setLocation(session.redirectTo());
              response.getHeaders().set("Cache-Control", "no-store");
              return response.setComplete();
            });
  }
}
