package br.com.banco.spider.operational.capacity;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.io.InputStream;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.Set;
import org.springframework.core.io.ClassPathResource;

/**
 * Carrega e valida o catálogo versionado de políticas de capacidade. Falha rápido no bootstrap: o
 * módulo nunca opera com catálogo ambíguo, porque um empate de precedência tornaria a decisão de
 * admissão dependente da ordem de leitura do arquivo.
 */
public class CapacityPolicyCatalog {

  public static final String POLICIES_PATH = "implementation/capacity-policies-v1.json";

  private final List<CapacityPolicy> policies;

  public CapacityPolicyCatalog(ObjectMapper mapper) {
    this(load(mapper));
  }

  public CapacityPolicyCatalog(List<CapacityPolicy> policies) {
    validate(policies);
    this.policies = List.copyOf(policies);
  }

  private static List<CapacityPolicy> load(ObjectMapper mapper) {
    try (InputStream input = new ClassPathResource(POLICIES_PATH).getInputStream()) {
      return mapper.readValue(input, new TypeReference<List<CapacityPolicy>>() {});
    } catch (Exception failure) {
      throw new IllegalStateException("Could not load capacity policy catalog", failure);
    }
  }

  private static void validate(List<CapacityPolicy> candidates) {
    if (candidates == null || candidates.isEmpty()) {
      throw new IllegalStateException("Capacity policy catalog must declare at least one policy");
    }
    Set<String> scopeKeys = new LinkedHashSet<>();
    Set<String> refs = new LinkedHashSet<>();
    Map<String, String> precedenceOwners = new LinkedHashMap<>();
    for (CapacityPolicy policy : candidates) {
      if (!scopeKeys.add(policy.scopeKey())) {
        throw new IllegalStateException("Duplicate capacity scope: " + policy.scopeKey());
      }
      if (!refs.add(policy.ref())) {
        throw new IllegalStateException("Duplicate capacity policy ref: " + policy.ref());
      }
      String precedenceKey = policy.scopeType().name() + "#" + policy.precedence();
      String previous = precedenceOwners.put(precedenceKey, policy.ref());
      if (previous != null) {
        throw new IllegalStateException(
            "Conflicting capacity precedence "
                + policy.precedence()
                + " for scope type "
                + policy.scopeType()
                + ": "
                + previous
                + " and "
                + policy.ref());
      }
    }
  }

  public List<CapacityPolicy> policies() {
    return policies;
  }

  public Optional<CapacityPolicy> findByRef(String ref) {
    if (ref == null || ref.isBlank()) {
      return Optional.empty();
    }
    return policies.stream().filter(policy -> policy.ref().equals(ref.trim())).findFirst();
  }

  /** Política efetiva do pedido: vence o escopo mais específico. */
  public Optional<CapacityPolicy> resolve(AdmissionRequest request) {
    return resolve(policies, request);
  }

  /**
   * Resolução isolada da validação de carga, para que o empate seja verificável mesmo quando o
   * catálogo publicado nunca o permite.
   */
  static Optional<CapacityPolicy> resolve(List<CapacityPolicy> candidates, AdmissionRequest request) {
    if (candidates == null || request == null) {
      return Optional.empty();
    }
    List<CapacityPolicy> matches = new ArrayList<>();
    int bestSpecificity = -1;
    for (CapacityPolicy policy : candidates) {
      String ref = request.refFor(policy.scopeType());
      if (ref == null || !ref.equals(policy.scopeRef())) {
        continue;
      }
      int specificity = policy.scopeType().specificity();
      if (specificity > bestSpecificity) {
        bestSpecificity = specificity;
        matches.clear();
        matches.add(policy);
      } else if (specificity == bestSpecificity) {
        matches.add(policy);
      }
    }
    if (matches.isEmpty()) {
      return Optional.empty();
    }
    if (matches.size() == 1) {
      return Optional.of(matches.getFirst());
    }
    int highest = matches.stream().mapToInt(CapacityPolicy::precedence).max().orElse(0);
    List<CapacityPolicy> winners =
        matches.stream().filter(policy -> policy.precedence() == highest).toList();
    if (winners.size() > 1) {
      throw new IllegalStateException(
          "Ambiguous capacity policy precedence "
              + highest
              + " for scope "
              + winners.getFirst().scopeKey());
    }
    return Optional.of(winners.getFirst());
  }
}
