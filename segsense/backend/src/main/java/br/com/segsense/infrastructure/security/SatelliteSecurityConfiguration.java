package br.com.segsense.infrastructure.security;

import br.com.segsense.inbound.http.security.JsonAccessDeniedHandler;
import br.com.segsense.inbound.http.security.JsonAuthenticationEntryPoint;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.HttpMethod;
import org.springframework.security.config.Customizer;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.annotation.web.configuration.EnableWebSecurity;
import org.springframework.security.config.annotation.web.configurers.AbstractHttpConfigurer;
import org.springframework.security.config.http.SessionCreationPolicy;
import org.springframework.security.web.SecurityFilterChain;
import org.springframework.security.web.savedrequest.NullRequestCache;

@Configuration
@EnableWebSecurity
public class SatelliteSecurityConfiguration {

  @Bean
  SecurityFilterChain satelliteSecurityFilterChain(
      HttpSecurity http,
      JsonAuthenticationEntryPoint authenticationEntryPoint,
      JsonAccessDeniedHandler accessDeniedHandler)
      throws Exception {
    http.csrf(csrf -> csrf.ignoringRequestMatchers("/api/**"))
        .cors(Customizer.withDefaults())
        .formLogin(AbstractHttpConfigurer::disable)
        .httpBasic(AbstractHttpConfigurer::disable)
        .logout(AbstractHttpConfigurer::disable)
        .requestCache(cache -> cache.requestCache(new NullRequestCache()))
        .sessionManagement(session -> session.sessionCreationPolicy(SessionCreationPolicy.STATELESS))
        .exceptionHandling(
            exceptions ->
                exceptions
                    .authenticationEntryPoint(authenticationEntryPoint)
                    .accessDeniedHandler(accessDeniedHandler))
        .authorizeHttpRequests(
            authorize ->
                authorize
                    .requestMatchers(HttpMethod.GET, "/api/v1/system/info")
                    .permitAll()
                    .requestMatchers(HttpMethod.GET, "/api/v1/public/context-links/*")
                    .permitAll()
                    .requestMatchers(HttpMethod.POST, "/api/v1/public/context-links/*/context-instances")
                    .permitAll()
                    .requestMatchers(
                        HttpMethod.GET, "/api/v1/public/context-links/*/context-instances/current")
                    .permitAll()
                    .requestMatchers(
                        HttpMethod.PUT,
                        "/api/v1/public/context-links/*/context-instances/current/values")
                    .permitAll()
                    .requestMatchers(
                        HttpMethod.POST,
                        "/api/v1/public/context-links/*/context-instances/current/authorize",
                        "/api/v1/public/context-links/*/context-instances/current/withdraw")
                    .permitAll()
                    .requestMatchers(HttpMethod.GET, "/api/v1/public/demonstrations/*")
                    .permitAll()
                    .requestMatchers(HttpMethod.GET, "/api/v1/public/demo/protection-journeys/*")
                    .permitAll()
                    .requestMatchers(HttpMethod.POST, "/api/v1/public/demo/protection-journeys")
                    .permitAll()
                    .requestMatchers(HttpMethod.POST, "/api/v1/public/demo/legacy-protection-journeys")
                    .permitAll()
                    .requestMatchers(HttpMethod.GET, "/api/v1/public/demo/context-sources")
                    .permitAll()
                    .requestMatchers(HttpMethod.POST, "/api/v1/public/demo/context-sources/resolve")
                    .permitAll()
                    .requestMatchers(HttpMethod.POST, "/api/v1/public/demo/url-captures")
                    .permitAll()
                    .requestMatchers(HttpMethod.GET, "/api/v1/public/demo/url-captures/*")
                    .permitAll()
                    .requestMatchers(HttpMethod.POST, "/api/v1/public/demo/url-captures/*/confirmations")
                    .permitAll()
                    .requestMatchers(HttpMethod.GET, "/api/v1/admin/demonstrations", "/api/v1/admin/demonstrations/**")
                    .hasAuthority(DemonstrationAuthorities.READ)
                    .requestMatchers(
                        HttpMethod.POST,
                        "/api/v1/admin/demonstrations",
                        "/api/v1/admin/demonstrations/*/draft",
                        "/api/v1/admin/demonstrations/*/submit",
                        "/api/v1/admin/demonstrations/*/return",
                        "/api/v1/admin/demonstrations/*/revisions")
                    .hasAuthority(DemonstrationAuthorities.WRITE)
                    .requestMatchers(HttpMethod.POST, "/api/v1/admin/demonstrations/*/approve")
                    .hasAuthority(DemonstrationAuthorities.APPROVE)
                    .requestMatchers(
                        HttpMethod.POST,
                        "/api/v1/admin/demonstrations/*/publish",
                        "/api/v1/admin/demonstrations/*/pause",
                        "/api/v1/admin/demonstrations/*/resume",
                        "/api/v1/admin/demonstrations/*/retire")
                    .hasAuthority(DemonstrationAuthorities.PUBLISH)
                    .requestMatchers(HttpMethod.OPTIONS, "/api/**")
                    .permitAll()
                    .requestMatchers(HttpMethod.GET, "/actuator/health", "/actuator/health/readiness")
                    .permitAll()
                    .requestMatchers(
                        HttpMethod.GET,
                        "/api/v1/admin/publishers/*/channels/*/environments/*/opportunities/*/consent-notice")
                    .hasAuthority(ConsentAuthorities.READ)
                    .requestMatchers(
                        HttpMethod.POST,
                        "/api/v1/admin/publishers/*/channels/*/environments/*/opportunities/*/consent-notice",
                        "/api/v1/admin/publishers/*/channels/*/environments/*/opportunities/*/consent-notice/draft",
                        "/api/v1/admin/publishers/*/channels/*/environments/*/opportunities/*/consent-notice/retire")
                    .hasAuthority(ConsentAuthorities.WRITE)
                    .requestMatchers(
                        HttpMethod.POST,
                        "/api/v1/admin/publishers/*/channels/*/environments/*/opportunities/*/consent-notice/approve")
                    .hasAuthority(ConsentAuthorities.APPROVE)
                    .requestMatchers(
                        HttpMethod.GET,
                        "/api/v1/admin/publishers/*/channels/*/environments/*/opportunities/*/links",
                        "/api/v1/admin/publishers/*/channels/*/environments/*/opportunities/*/links/**")
                    .hasAuthority(LinkAuthorities.READ)
                    .requestMatchers(
                        HttpMethod.POST,
                        "/api/v1/admin/publishers/*/channels/*/environments/*/opportunities/*/links",
                        "/api/v1/admin/publishers/*/channels/*/environments/*/opportunities/*/links/*/revoke")
                    .hasAuthority(LinkAuthorities.MANAGE)
                    .requestMatchers(
                        HttpMethod.GET,
                        "/api/v1/admin/publishers/*/channels/*/environments/*/opportunities",
                        "/api/v1/admin/publishers/*/channels/*/environments/*/opportunities/**")
                    .hasAuthority(OpportunityAuthorities.READ)
                    .requestMatchers(
                        HttpMethod.POST,
                        "/api/v1/admin/publishers/*/channels/*/environments/*/opportunities/*/governance/submit")
                    .hasAuthority(OpportunityAuthorities.SUBMIT)
                    .requestMatchers(
                        HttpMethod.POST,
                        "/api/v1/admin/publishers/*/channels/*/environments/*/opportunities/*/governance/return-for-changes",
                        "/api/v1/admin/publishers/*/channels/*/environments/*/opportunities/*/governance/approve",
                        "/api/v1/admin/publishers/*/channels/*/environments/*/opportunities/*/governance/reject")
                    .hasAuthority(OpportunityAuthorities.REVIEW)
                    .requestMatchers(
                        HttpMethod.POST,
                        "/api/v1/admin/publishers/*/channels/*/environments/*/opportunities/*/publication/**")
                    .hasAuthority(PublicationAuthorities.MANAGE)
                    .requestMatchers(
                        HttpMethod.POST,
                        "/api/v1/admin/publishers/*/channels/*/environments/*/opportunities",
                        "/api/v1/admin/publishers/*/channels/*/environments/*/opportunities/**")
                    .hasAuthority(OpportunityAuthorities.WRITE)
                    .requestMatchers(
                        HttpMethod.PUT,
                        "/api/v1/admin/publishers/*/channels/*/environments/*/opportunities",
                        "/api/v1/admin/publishers/*/channels/*/environments/*/opportunities/**")
                    .denyAll()
                    .requestMatchers(
                        HttpMethod.PATCH,
                        "/api/v1/admin/publishers/*/channels/*/environments/*/opportunities",
                        "/api/v1/admin/publishers/*/channels/*/environments/*/opportunities/**")
                    .denyAll()
                    .requestMatchers(
                        HttpMethod.DELETE,
                        "/api/v1/admin/publishers/*/channels/*/environments/*/opportunities",
                        "/api/v1/admin/publishers/*/channels/*/environments/*/opportunities/**")
                    .denyAll()
                    .requestMatchers(HttpMethod.GET, "/api/v1/admin/**")
                    .hasAuthority(CatalogAuthorities.READ)
                    .requestMatchers(HttpMethod.POST, "/api/v1/admin/**")
                    .hasAuthority(CatalogAuthorities.WRITE)
                    .requestMatchers(HttpMethod.PATCH, "/api/v1/admin/**")
                    .hasAuthority(CatalogAuthorities.WRITE)
                    .anyRequest()
                    .denyAll());
    return http.build();
  }
}
