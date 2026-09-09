package br.com.banco.spider.integration.inbound.http.contextuallink;

import br.com.banco.spider.contextuallink.application.SpiderBankUnderstandService;
import br.com.banco.spider.contextuallink.application.SpiderBankUnderstandService.UnderstandCommand;
import java.util.Map;
import org.springframework.boot.autoconfigure.condition.ConditionalOnBean;
import org.springframework.context.annotation.Profile;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RestController;
import reactor.core.publisher.Mono;

@RestController
@Profile("local-demo")
@ConditionalOnBean(SpiderBankUnderstandService.class)
public class SpiderBankUnderstandApiController {

  private final SpiderBankUnderstandService understand;

  public SpiderBankUnderstandApiController(SpiderBankUnderstandService understand) {
    this.understand = understand;
  }

  @PostMapping("/v1/demo/spiderbank/understand")
  public Mono<Map<String, Object>> understand(@RequestBody UnderstandRequest body) {
    UnderstandRequest payload = body == null ? new UnderstandRequest(null, null, null, null) : body;
    return understand.understand(
        new UnderstandCommand(
            payload.contextId(), payload.objective(), payload.amount(), payload.decisionId()));
  }

  public record UnderstandRequest(String contextId, String objective, String amount, String decisionId) {}
}
