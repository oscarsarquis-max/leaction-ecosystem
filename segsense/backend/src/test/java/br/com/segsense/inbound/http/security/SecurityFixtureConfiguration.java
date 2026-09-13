package br.com.segsense.inbound.http.security;

import java.util.Map;
import org.springframework.boot.test.context.TestConfiguration;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@TestConfiguration
public class SecurityFixtureConfiguration {

  @RestController
  @RequestMapping("/api/v1/system/security-fixture")
  static class SecurityFixtureController {

    @GetMapping("/protected")
    Map<String, String> protectedResource() {
      return Map.of("status", "fixture-must-not-succeed-without-policy");
    }
  }
}
