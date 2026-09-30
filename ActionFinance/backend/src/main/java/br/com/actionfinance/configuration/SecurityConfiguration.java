package br.com.actionfinance.configuration;

import br.com.actionfinance.infrastructure.security.AuthorizationRefreshFilter;
import br.com.actionfinance.infrastructure.security.CsrfCookieFilter;
import br.com.actionfinance.infrastructure.security.DemoBearerAuthenticationFilter;
import br.com.actionfinance.infrastructure.security.JsonAccessDeniedHandler;
import br.com.actionfinance.infrastructure.security.JsonAuthenticationEntryPoint;
import jakarta.servlet.DispatcherType;
import org.springframework.beans.factory.ObjectProvider;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.HttpMethod;
import org.springframework.security.config.Customizer;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.annotation.web.configuration.EnableWebSecurity;
import org.springframework.security.config.annotation.web.configurers.AbstractHttpConfigurer;
import org.springframework.security.config.http.SessionCreationPolicy;
import org.springframework.security.web.SecurityFilterChain;
import org.springframework.security.web.authentication.AuthenticationFailureHandler;
import org.springframework.security.web.authentication.AuthenticationSuccessHandler;
import org.springframework.security.web.authentication.UsernamePasswordAuthenticationFilter;
import org.springframework.security.web.csrf.CookieCsrfTokenRepository;
import org.springframework.security.web.csrf.CsrfFilter;
import org.springframework.security.web.csrf.CsrfTokenRequestAttributeHandler;
import org.springframework.security.web.savedrequest.NullRequestCache;
import org.springframework.security.web.util.matcher.AntPathRequestMatcher;
import org.springframework.web.cors.CorsConfiguration;
import org.springframework.web.cors.CorsConfigurationSource;
import org.springframework.web.cors.UrlBasedCorsConfigurationSource;

import java.util.ArrayList;
import java.util.List;

@Configuration
@EnableWebSecurity
public class SecurityConfiguration {

    @Bean
    SecurityFilterChain securityFilterChain(
            HttpSecurity http,
            ActionFinanceProperties properties,
            JsonAuthenticationEntryPoint authenticationEntryPoint,
            JsonAccessDeniedHandler accessDeniedHandler,
            ObjectProvider<DemoBearerAuthenticationFilter> demoFilter,
            ObjectProvider<AuthorizationRefreshFilter> refreshFilter,
            ObjectProvider<AuthenticationSuccessHandler> oidcSuccess,
            ObjectProvider<AuthenticationFailureHandler> oidcFailure)
            throws Exception {
        boolean oidc = properties.getOidc().isEnabled();
        http.cors(Customizer.withDefaults())
                .formLogin(AbstractHttpConfigurer::disable)
                .httpBasic(AbstractHttpConfigurer::disable)
                .requestCache(cache -> cache.requestCache(new NullRequestCache()))
                .exceptionHandling(
                        exceptions ->
                                exceptions
                                        .defaultAuthenticationEntryPointFor(
                                                authenticationEntryPoint, new AntPathRequestMatcher("/api/**"))
                                        .accessDeniedHandler(accessDeniedHandler));
        if (oidc) {
            CookieCsrfTokenRepository csrfRepository = CookieCsrfTokenRepository.withHttpOnlyFalse();
            csrfRepository.setCookiePath("/");
            csrfRepository.setCookieCustomizer(cookie -> cookie.sameSite("Lax").secure(properties.getSession().isCookieSecure()));
            http.csrf(
                            csrf ->
                                    csrf.csrfTokenRepository(csrfRepository)
                                            .csrfTokenRequestHandler(new CsrfTokenRequestAttributeHandler()))
                    .sessionManagement(
                            session ->
                                    session.sessionCreationPolicy(SessionCreationPolicy.IF_REQUIRED)
                                            .sessionFixation()
                                            .changeSessionId())
                    .oauth2Login(
                            login ->
                                    login.loginPage(
                                                    "/oauth2/authorization/"
                                                            + properties.getLoginRegistrationId())
                                            .successHandler(oidcSuccess.getObject())
                                            .failureHandler(oidcFailure.getObject()))
                    .logout(
                            logout ->
                                    logout.logoutUrl("/logout")
                                            .logoutSuccessHandler(
                                                    (request, response, authentication) -> {
                                                        String accept = request.getHeader("Accept");
                                                        if (accept != null && accept.contains("application/json")) {
                                                            response.setStatus(204);
                                                            return;
                                                        }
                                                        response.sendRedirect(
                                                                properties.getPublicOrigin().replaceAll("/$", "")
                                                                        + "/?logout=1");
                                                    })
                                            .invalidateHttpSession(true)
                                            .clearAuthentication(true)
                                            .deleteCookies("AFSESSION", "XSRF-TOKEN"));
            http.addFilterAfter(new CsrfCookieFilter(), CsrfFilter.class);
            AuthorizationRefreshFilter refresh = refreshFilter.getIfAvailable();
            if (refresh != null) {
                http.addFilterAfter(refresh, UsernamePasswordAuthenticationFilter.class);
            }
        } else {
            http.csrf(AbstractHttpConfigurer::disable)
                    .logout(AbstractHttpConfigurer::disable)
                    .sessionManagement(session -> session.sessionCreationPolicy(SessionCreationPolicy.STATELESS));
            DemoBearerAuthenticationFilter filter = demoFilter.getIfAvailable();
            if (filter != null) {
                http.addFilterBefore(filter, UsernamePasswordAuthenticationFilter.class);
            }
        }
        http.authorizeHttpRequests(
                authorize -> {
                    authorize.dispatcherTypeMatchers(DispatcherType.ERROR).permitAll();
                    authorize.requestMatchers(HttpMethod.GET, "/api/v1/system/info").permitAll();
                    authorize.requestMatchers(
                                    HttpMethod.GET,
                                    "/actuator/health",
                                    "/actuator/health/liveness",
                                    "/actuator/health/readiness")
                            .permitAll();
                    if (oidc) {
                        authorize.requestMatchers(
                                        "/",
                                        "/index.html",
                                        "/favicon.ico",
                                        "/assets/**",
                                        "/receivables/**",
                                        "/payables/**",
                                        "/financial-accounts/**",
                                        "/catalogs/**",
                                        "/access-pending",
                                        "/oauth2/**",
                                        "/login/oauth2/**")
                                .permitAll();
                        authorize.requestMatchers(HttpMethod.GET, "/api/v1/access/csrf").permitAll();
                        authorize.requestMatchers(HttpMethod.GET, "/api/v1/access/me").authenticated();
                        authorize.requestMatchers(HttpMethod.POST, "/logout").authenticated();
                    } else {
                        authorize.requestMatchers(HttpMethod.GET, "/api/v1/access/me").hasAuthority("system:read");
                    }
                    authorize
                            .requestMatchers(HttpMethod.GET, "/api/v1/access/context")
                            .hasAuthority("company-context:read")
                            .requestMatchers(HttpMethod.GET, "/api/v1/financial-accounts", "/api/v1/financial-accounts/**")
                            .hasAuthority("financial-accounts:read")
                            .requestMatchers(HttpMethod.POST, "/api/v1/financial-accounts")
                            .hasAuthority("financial-accounts:write")
                            .requestMatchers(HttpMethod.PATCH, "/api/v1/financial-accounts/**")
                            .hasAuthority("financial-accounts:write")
                            .requestMatchers(
                                    HttpMethod.GET,
                                    "/api/v1/receivables/*/settlements",
                                    "/api/v1/payables/*/settlements")
                            .hasAuthority("settlements:read")
                            .requestMatchers(
                                    HttpMethod.POST,
                                    "/api/v1/receivables/*/settlements",
                                    "/api/v1/payables/*/settlements")
                            .hasAuthority("settlements:write")
                            .requestMatchers(HttpMethod.GET, "/api/v1/settlements/*")
                            .hasAuthority("settlements:read")
                            .requestMatchers(HttpMethod.POST, "/api/v1/settlements/*/reversal")
                            .hasAuthority("settlements:reverse")
                            .requestMatchers(HttpMethod.GET, "/api/v1/receivables/**", "/api/v1/payables/**")
                            .hasAuthority("titles:read")
                            .requestMatchers(HttpMethod.POST, "/api/v1/receivables/**", "/api/v1/payables/**")
                            .hasAuthority("titles:write")
                            .requestMatchers(HttpMethod.PATCH, "/api/v1/receivables/**", "/api/v1/payables/**")
                            .hasAuthority("titles:write")
                            .requestMatchers(HttpMethod.GET, "/api/v1/catalogs/**")
                            .hasAuthority("catalogs:read")
                            .requestMatchers(HttpMethod.POST, "/api/v1/catalogs/**")
                            .hasAuthority("catalogs:write")
                            .requestMatchers(HttpMethod.PATCH, "/api/v1/catalogs/**")
                            .hasAuthority("catalogs:write")
                            .anyRequest()
                            .denyAll();
                });
        return http.build();
    }

    @Bean
    CorsConfigurationSource corsConfigurationSource(ActionFinanceProperties properties) {
        CorsConfiguration configuration = new CorsConfiguration();
        configuration.setAllowedOrigins(properties.getCors().getAllowedOrigins());
        configuration.setAllowedMethods(List.of("GET", "HEAD", "OPTIONS", "POST", "PATCH"));
        List<String> headers = new ArrayList<>(List.of("Authorization", "X-Correlation-Id", "Content-Type", "Idempotency-Key"));
        if (properties.getOidc().isEnabled()) {
            headers.add("X-XSRF-TOKEN");
            configuration.setAllowCredentials(true);
        } else {
            configuration.setAllowCredentials(false);
        }
        configuration.setAllowedHeaders(headers);
        UrlBasedCorsConfigurationSource source = new UrlBasedCorsConfigurationSource();
        source.registerCorsConfiguration("/**", configuration);
        return source;
    }
}
