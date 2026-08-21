package br.com.banco.spider.config;

import io.swagger.v3.oas.models.OpenAPI;
import io.swagger.v3.oas.models.info.Info;
import io.swagger.v3.oas.models.security.SecurityScheme;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

@Configuration
public class OpenApiConfig {

  @Bean
  OpenAPI spiderOpenApi() {
    return new OpenAPI()
        .info(
            new Info()
                .title("Spider Orchestrator API")
                .version("1.0")
                .description(
                    """
                    Baseline legado: POST /v1/products/orchestrate.

                    Perfil canônico HTTP (PROMPT-006) — endpoints condicionais (default disabled):
                    - POST /v1/canonical/executions (spider.canonical.http.enabled)
                    - GET /v1/canonical/executions/{id} (+ status-query-enabled)
                    - POST /v1/canonical/signals (spider.canonical.signal-http.enabled)

                    Segurança: requisito abstrato de autenticação de originador/source (deny-by-default).
                    Sem URL/fila/tópico livres; Sem IdP produtivo neste incremento.
                    """))
        .schemaRequirement(
            "SpiderCredentialRef",
            new SecurityScheme()
                .type(SecurityScheme.Type.APIKEY)
                .in(SecurityScheme.In.HEADER)
                .name("X-Spider-Credential-Ref")
                .description("Referência opaca de credential material — não é IdP corporativo."));
  }
}
