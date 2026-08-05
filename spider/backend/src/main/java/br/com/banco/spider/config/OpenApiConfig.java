package br.com.banco.spider.config;

import io.swagger.v3.oas.models.OpenAPI;
import io.swagger.v3.oas.models.info.Info;
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
                .description("Orquestrador reativo de contexto — rotas técnicas e traces")
                .version("0.1.0"));
  }
}
