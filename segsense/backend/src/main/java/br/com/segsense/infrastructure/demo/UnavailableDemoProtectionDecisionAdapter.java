package br.com.segsense.infrastructure.demo;

import br.com.segsense.application.demo.DemoProtectionDecisionGateway;
import org.springframework.boot.autoconfigure.condition.ConditionalOnMissingBean;
import org.springframework.stereotype.Component;

@Component
@ConditionalOnMissingBean(DemoProtectionDecisionGateway.class)
public class UnavailableDemoProtectionDecisionAdapter implements DemoProtectionDecisionGateway {

  @Override
  public Result submit(Command command) {
    return Result.spiderUnavailable();
  }
}
