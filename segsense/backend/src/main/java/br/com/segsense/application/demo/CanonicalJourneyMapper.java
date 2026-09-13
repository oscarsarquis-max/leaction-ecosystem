package br.com.segsense.application.demo;

import br.com.segsense.application.demo.DemoProtectionDecisionGateway.Item;
import br.com.segsense.application.demo.DemoProtectionDecisionGateway.Result;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

public final class CanonicalJourneyMapper {

  private CanonicalJourneyMapper() {}

  public static boolean blank(String value) {
    return value == null || value.isBlank() || "null".equals(value);
  }

  public static boolean preProposalConfirmed(Result result) {
    return result != null
        && result.spiderReached()
        && "PRE_PROPOSAL_READY".equals(result.status())
        && !blank(result.decisionId())
        && !blank(result.mockResultId());
  }

  @SuppressWarnings("unchecked")
  public static Result fromSatelliteResponse(Map<String, Object> node) {
    if (node == null || node.isEmpty()) {
      return Result.spiderUnavailable();
    }
    String mappedStatus = mapStatus(text(node, "status"));
    String decisionId = text(node, "decisionId");
    String contractVersion = text(node, "contractVersion");
    String capabilityId = text(node, "capabilityId");
    String providerRequestId = text(node, "providerRequestId");
    String requiredAction = text(node, "requiredAction");
    Map<String, Object> originProvenance = provenanceFrom(node.get("originProvenance"));
    List<Item> items = new ArrayList<>();
    List<String> pending = new ArrayList<>();
    String mockResultId = null;
    String mockOrigin = null;
    String providerId = null;
    Object summaryNode = node.get("resultSummary");
    if (summaryNode instanceof Map<?, ?> summary) {
      Map<String, Object> summaryMap = (Map<String, Object>) summary;
      mockResultId = text(summaryMap, "providerReference");
      mockOrigin = text(summaryMap, "origin");
      providerId = text(summaryMap, "providerId");
      if (summaryMap.get("items") instanceof List<?> rawItems) {
        for (Object raw : rawItems) {
          if (raw instanceof Map<?, ?> item) {
            Map<String, Object> itemMap = (Map<String, Object>) item;
            items.add(
                new Item(
                    text(itemMap, "code"),
                    text(itemMap, "title"),
                    text(itemMap, "kind"),
                    Boolean.TRUE.equals(itemMap.get("notOfferable"))));
          }
        }
      }
      if (summaryMap.get("pendingForHumanReview") instanceof List<?> rawPending) {
        for (Object raw : rawPending) {
          pending.add(String.valueOf(raw));
        }
      }
    }
    boolean providerConfirmed =
        "PRE_PROPOSAL_READY".equals(mappedStatus) && !blank(decisionId) && !blank(mockResultId);
    if ("PRE_PROPOSAL_READY".equals(mappedStatus) && !providerConfirmed) {
      mappedStatus = "INCOMPLETE_CANONICAL";
    }
    if (!providerConfirmed) {
      items = List.of();
      pending = List.of();
    }
    String failureKind = null;
    if ("MOCK_UNAVAILABLE".equals(mappedStatus)) {
      failureKind = "MOCK";
    } else if ("REJECTED".equals(mappedStatus)) {
      failureKind = "VALIDATION";
    } else if ("INCOMPLETE_CANONICAL".equals(mappedStatus)) {
      failureKind = "INCOMPLETE";
    }
    return new Result(
        true,
        mappedStatus,
        decisionId,
        text(node, "explanation"),
        "SPIDER_SATELLITE_CONTRACT_V1",
        text(node, "watermark"),
        providerConfirmed,
        providerConfirmed ? mockResultId : null,
        providerConfirmed ? mockOrigin : null,
        providerConfirmed ? providerId : null,
        items,
        pending,
        originProvenance,
        text(node, "spiderPath"),
        failureKind,
        contractVersion,
        providerConfirmed ? capabilityId : null,
        providerConfirmed ? providerRequestId : null,
        requiredAction);
  }

  private static String mapStatus(String status) {
    if ("READY".equals(status)) {
      return "PRE_PROPOSAL_READY";
    }
    if ("PROVIDER_UNAVAILABLE".equals(status)) {
      return "MOCK_UNAVAILABLE";
    }
    return status;
  }

  @SuppressWarnings("unchecked")
  static Map<String, Object> provenanceFrom(Object origin) {
    if (!(origin instanceof Map<?, ?> map)) {
      return Map.of();
    }
    Map<String, Object> provenance = new LinkedHashMap<>((Map<String, Object>) origin);
    if (map.get("attributes") instanceof Map<?, ?> attributes) {
      Object channel = ((Map<?, ?>) attributes).get("channel");
      if (channel != null) {
        provenance.putIfAbsent("channel", channel);
      }
    }
    return provenance;
  }

  private static String text(Map<String, Object> node, String field) {
    Object value = node.get(field);
    if (value == null) {
      return null;
    }
    String text = String.valueOf(value);
    return blank(text) ? null : text;
  }
}
