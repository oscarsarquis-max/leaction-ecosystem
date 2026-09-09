package br.com.banco.spider.integration.inbound.http.contextuallink;

import br.com.banco.spider.config.ContextualLinkProperties;
import java.nio.charset.StandardCharsets;
import br.com.banco.spider.contextuallink.application.ContextualLinkGatewayService;
import org.springframework.boot.autoconfigure.condition.ConditionalOnBean;
import org.springframework.context.annotation.Profile;
import org.springframework.core.io.ClassPathResource;
import org.springframework.http.MediaType;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;
import reactor.core.publisher.Mono;

@RestController
@Profile("local-demo")
@ConditionalOnBean(ContextualLinkGatewayService.class)
public class PartnerNewsPageController {

  private final ContextualLinkProperties properties;

  public PartnerNewsPageController(ContextualLinkProperties properties) {
    this.properties = properties;
  }

  @GetMapping(value = {"/demo/partner/agro-hoje", "/demo/partner/agro-hoje/"}, produces = MediaType.TEXT_HTML_VALUE)
  public Mono<String> page() {
    return Mono.fromCallable(
        () -> {
          ClassPathResource resource = new ClassPathResource("demo/partner/agro-hoje.html");
          String html = resource.getContentAsString(StandardCharsets.UTF_8);
          return html.replace("{{GATEWAY_URL}}", properties.gatewayPublicUrl());
        });
  }

  @GetMapping(value = {"/demo/partner/hero.jpg", "/demo/partner/agro-hoje/hero.jpg"}, produces = MediaType.IMAGE_JPEG_VALUE)
  public Mono<byte[]> hero() {
    return Mono.fromCallable(
        () -> new ClassPathResource("demo/partner/hero.jpg").getContentAsByteArray());
  }
}
