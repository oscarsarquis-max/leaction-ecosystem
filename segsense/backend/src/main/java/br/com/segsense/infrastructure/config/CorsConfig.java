package br.com.segsense.infrastructure.config;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Configuration;
import org.springframework.web.servlet.config.annotation.CorsRegistry;
import org.springframework.web.servlet.config.annotation.WebMvcConfigurer;

@Configuration
public class CorsConfig implements WebMvcConfigurer {

  private final String[] allowedOrigins;

  public CorsConfig(@Value("${segsense.cors.allowed-origin}") String allowedOrigin) {
    this.allowedOrigins = CorsAllowedOrigins.parse(allowedOrigin);
  }

  @Override
  public void addCorsMappings(CorsRegistry registry) {
    registry
        .addMapping("/api/**")
        .allowedOrigins(allowedOrigins)
        .allowedMethods("GET", "POST", "PUT", "PATCH", "OPTIONS")
        .allowedHeaders(
            "Accept",
            "Content-Type",
            "X-Correlation-ID",
            "X-SegSense-Instance-Credential",
            "Idempotency-Key")
        .exposedHeaders("X-Correlation-ID")
        .allowCredentials(false);
  }
}
