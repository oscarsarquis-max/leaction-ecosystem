package br.com.banco.spider.application.console;

import br.com.banco.spider.config.OperationalConsoleProperties;
import br.com.banco.spider.operational.events.OperationalEvent;
import br.com.banco.spider.operational.events.OperationalEventType;
import br.com.banco.spider.operational.readmodel.OperationalEventView;
import java.util.Arrays;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.Set;
import java.util.stream.Collectors;
import org.springframework.stereotype.Component;

@Component
public class MonitorCompanyAccess {

  private final OperationalConsoleProperties properties;

  public MonitorCompanyAccess(OperationalConsoleProperties properties) {
    this.properties = properties;
  }

  public boolean enabled() {
    return properties.getCompanyScope().isEnabled();
  }

  public Set<String> allowedCompanies(OperationalConsoleSecurityContext ctx) {
    if (ctx == null || !ctx.authenticated()) {
      return Set.of();
    }
    Map<String, String> bindings = properties.getCompanyScope().getBindings();
    String raw = firstNonBlank(bindings.get(ctx.principalRef()), bindings.get(ctx.principalRef().toLowerCase()));
    if (raw == null || raw.isBlank()) {
      return Set.of();
    }
    return Arrays.stream(raw.split(","))
        .map(String::trim)
        .filter(value -> !value.isBlank())
        .collect(Collectors.toCollection(LinkedHashSet::new));
  }

  public Optional<String> companyOfViews(List<OperationalEventView> events) {
    if (events == null) {
      return Optional.empty();
    }
    return events.stream().map(this::companyOf).flatMap(Optional::stream).findFirst();
  }

  public Optional<String> companyOfEvents(List<OperationalEvent> events) {
    if (events == null) {
      return Optional.empty();
    }
    return events.stream().map(this::companyOf).flatMap(Optional::stream).findFirst();
  }

  public Optional<String> companyOf(OperationalEventView event) {
    if (event == null) {
      return Optional.empty();
    }
    return companyOf(event.metadata(), event.eventType());
  }

  public Optional<String> companyOf(OperationalEvent event) {
    if (event == null) {
      return Optional.empty();
    }
    return companyOf(event.metadata(), event.eventType());
  }

  public Optional<String> companyOf(Map<String, String> metadata, OperationalEventType type) {
    if (metadata != null) {
      String company = text(metadata.get("companyId"));
      if (!company.isBlank()) {
        return Optional.of(company);
      }
    }
    if (type == OperationalEventType.SATELLITE_COMPANY_AUTHORIZED && metadata != null) {
      String reason = text(metadata.get("reasonCode"));
      if (!reason.isBlank()) {
        return Optional.of(reason);
      }
    }
    return Optional.empty();
  }

  public boolean maySee(OperationalConsoleSecurityContext ctx, Optional<String> company) {
    return maySee(ctx, company, false);
  }

  public boolean maySee(
      OperationalConsoleSecurityContext ctx, Optional<String> company, boolean canonicalFlow) {
    if (!enabled()) {
      return true;
    }
    if (ctx == null || !ctx.authenticated()) {
      return false;
    }
    if (company.isPresent() && !company.get().isBlank()) {
      return allowedCompanies(ctx).contains(company.get());
    }
    return canonicalFlow && maySeeCanonical(ctx);
  }

  public boolean maySeeCanonical(OperationalConsoleSecurityContext ctx) {
    if (ctx == null || !ctx.authenticated()) {
      return false;
    }
    String raw = properties.getCompanyScope().getCanonicalPrincipals();
    if (raw == null || raw.isBlank()) {
      return false;
    }
    return Arrays.stream(raw.split(","))
        .map(String::trim)
        .anyMatch(value -> value.equals(ctx.principalRef()) || value.equalsIgnoreCase(ctx.principalRef()));
  }

  public boolean looksCanonical(List<OperationalEventView> events) {
    if (events == null || events.isEmpty()) {
      return false;
    }
    boolean satellite = events.stream().anyMatch(event -> event.eventType() != null && event.eventType().name().startsWith("SATELLITE_"));
    boolean started =
        events.stream()
            .anyMatch(
                event ->
                    event.eventType() == OperationalEventType.EXECUTION_STARTED
                        || event.eventType() == OperationalEventType.EXECUTION_SUCCEEDED
                        || event.eventType() == OperationalEventType.EXECUTION_REJECTED);
    return started && !satellite;
  }

  public boolean looksCanonicalEvents(List<OperationalEvent> events) {
    if (events == null || events.isEmpty()) {
      return false;
    }
    boolean satellite = events.stream().anyMatch(event -> event.eventType() != null && event.eventType().name().startsWith("SATELLITE_"));
    boolean started =
        events.stream()
            .anyMatch(
                event ->
                    event.eventType() == OperationalEventType.EXECUTION_STARTED
                        || event.eventType() == OperationalEventType.EXECUTION_SUCCEEDED
                        || event.eventType() == OperationalEventType.EXECUTION_REJECTED);
    return started && !satellite;
  }

  private static String firstNonBlank(String left, String right) {
    if (left != null && !left.isBlank()) {
      return left;
    }
    return right;
  }

  private static String text(String value) {
    return value == null ? "" : value.trim();
  }
}
