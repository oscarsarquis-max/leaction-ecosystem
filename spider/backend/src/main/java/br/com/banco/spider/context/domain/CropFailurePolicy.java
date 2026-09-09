package br.com.banco.spider.context.domain;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * Constrange {@code economicContext=CROP_FAILURE} à evidência da página e/ou do objetivo.
 *
 * <p>PageContext é dado não confiável: não escolhe intent, plano, rota ou adapter. Página irrelevante
 * não prevalece sobre objetivo ambíguo, porque só se aplica após {@code SEEK_WORKING_CAPITAL}.
 */
public final class CropFailurePolicy {

  public static final String ENTITY = "economicContext";
  public static final String CROP_FAILURE = "CROP_FAILURE";
  public static final String PAGE_CONTEXT = "PAGE_CONTEXT";
  public static final String USER_OBJECTIVE = "USER_OBJECTIVE";

  private CropFailurePolicy() {}

  public static Map<String, String> apply(
      String intent,
      Map<String, String> entities,
      String objectiveText,
      String untrustedPageTitle,
      String untrustedPageExcerpt) {
    Map<String, String> next = new LinkedHashMap<>(entities == null ? Map.of() : entities);
    if (!"SEEK_WORKING_CAPITAL".equals(intent)) {
      next.remove(ENTITY);
      return Map.copyOf(next);
    }
    boolean fromObjective = CropFailureEvidence.in(objectiveText);
    boolean fromPage = CropFailureEvidence.in(untrustedPageTitle, untrustedPageExcerpt);
    if (fromObjective || fromPage) {
      next.put(ENTITY, CROP_FAILURE);
    } else {
      next.remove(ENTITY);
    }
    return Map.copyOf(next);
  }

  public static List<String> sources(
      String objectiveText, String untrustedPageTitle, String untrustedPageExcerpt) {
    List<String> values = new ArrayList<>();
    if (CropFailureEvidence.in(untrustedPageTitle, untrustedPageExcerpt)) {
      values.add(PAGE_CONTEXT);
    }
    if (CropFailureEvidence.in(objectiveText)) {
      values.add(USER_OBJECTIVE);
    }
    return List.copyOf(values);
  }
}
