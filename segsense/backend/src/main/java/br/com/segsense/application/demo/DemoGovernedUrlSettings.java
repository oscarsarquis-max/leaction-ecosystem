package br.com.segsense.application.demo;

import java.util.Arrays;
import java.util.LinkedHashSet;
import java.util.Set;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

@Component
public class DemoGovernedUrlSettings {

  private final Set<Integer> allowedPorts;

  public DemoGovernedUrlSettings(
      @Value("${segsense.demo.governed-source.allowed-ports:5178}") String rawPorts) {
    this.allowedPorts = parsePorts(rawPorts);
  }

  public Set<Integer> allowedPorts() {
    return allowedPorts;
  }

  static Set<Integer> parsePorts(String raw) {
    Set<Integer> ports = new LinkedHashSet<>();
    if (raw == null || raw.isBlank()) {
      ports.add(5178);
      return Set.copyOf(ports);
    }
    Arrays.stream(raw.split(","))
        .map(String::trim)
        .filter(part -> !part.isEmpty())
        .map(Integer::parseInt)
        .forEach(ports::add);
    if (ports.isEmpty()) {
      ports.add(5178);
    }
    return Set.copyOf(ports);
  }
}
