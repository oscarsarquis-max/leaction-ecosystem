package br.com.segsense.domain.opportunity;

import br.com.segsense.domain.catalog.CatalogValidationException;
import java.time.Instant;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Objects;
import java.util.Set;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

public final class OpportunityContent {

  private static final Pattern PLACEHOLDER = Pattern.compile("\\{\\{([a-z][a-zA-Z0-9]{1,39})\\}\\}");

  private final String title;
  private final ContextMode contextMode;
  private final String contextSummaryTemplate;
  private final String objectiveTemplate;
  private final String callToActionLabel;
  private final Instant validFrom;
  private final Instant validUntil;
  private final List<ContextFieldDefinition> contextFields;

  private OpportunityContent(
      String title,
      ContextMode contextMode,
      String contextSummaryTemplate,
      String objectiveTemplate,
      String callToActionLabel,
      Instant validFrom,
      Instant validUntil,
      List<ContextFieldDefinition> contextFields) {
    this.title = title;
    this.contextMode = contextMode;
    this.contextSummaryTemplate = contextSummaryTemplate;
    this.objectiveTemplate = objectiveTemplate;
    this.callToActionLabel = callToActionLabel;
    this.validFrom = validFrom;
    this.validUntil = validUntil;
    this.contextFields = contextFields;
  }

  public static OpportunityContent parse(
      String title,
      ContextMode contextMode,
      String contextSummaryTemplate,
      String objectiveTemplate,
      String callToActionLabel,
      Instant validFrom,
      Instant validUntil,
      List<ContextFieldDefinition> fields) {
    Objects.requireNonNull(contextMode, "contextMode");
    String parsedTitle = OpportunityText.requiredLength(title, "O título", 5, 140);
    String summary =
        OpportunityText.requiredLength(contextSummaryTemplate, "O resumo de contexto", 10, 1000);
    String objective =
        OpportunityText.requiredLength(objectiveTemplate, "O modelo de objetivo", 10, 1000);
    String cta = OpportunityText.requiredLength(callToActionLabel, "A chamada para ação", 3, 80);
    if (validFrom != null && validUntil != null && !validUntil.isAfter(validFrom)) {
      throw new CatalogValidationException("validUntil deve ser posterior a validFrom.");
    }
    List<ContextFieldDefinition> ordered =
        fields == null ? List.of() : List.copyOf(fields);
    if (ordered.size() > 20) {
      throw new CatalogValidationException("A revisão admite no máximo 20 campos de contexto.");
    }
    if (contextMode == ContextMode.STATIC && !ordered.isEmpty()) {
      throw new CatalogValidationException("O modo STATIC não admite campos de contexto.");
    }
    if (contextMode == ContextMode.DYNAMIC && ordered.isEmpty()) {
      throw new CatalogValidationException("O modo DYNAMIC exige ao menos um campo de contexto.");
    }
    Set<String> keys = new HashSet<>();
    List<ContextFieldDefinition> normalized = new ArrayList<>();
    int index = 0;
    for (ContextFieldDefinition field : ordered) {
      if (!keys.add(field.key())) {
        throw new CatalogValidationException("A chave do campo não pode se repetir na revisão.");
      }
      if (field.position() != index) {
        normalized.add(
            ContextFieldDefinition.parse(
                field.key(),
                field.label(),
                field.type(),
                field.required(),
                field.source(),
                field.classification(),
                field.allowedValues(),
                index));
      } else {
        normalized.add(field);
      }
      index++;
    }
    Set<String> placeholders = placeholdersIn(summary);
    placeholders.addAll(placeholdersIn(objective));
    placeholders.addAll(placeholdersIn(cta));
    placeholders.addAll(placeholdersIn(parsedTitle));
    for (String placeholder : placeholders) {
      if (!keys.contains(placeholder)) {
        throw new CatalogValidationException(
            "O placeholder {{" + placeholder + "}} não corresponde a um campo declarado.");
      }
    }
    return new OpportunityContent(
        parsedTitle,
        contextMode,
        summary,
        objective,
        cta,
        validFrom,
        validUntil,
        List.copyOf(normalized));
  }

  public boolean sameAs(OpportunityContent other) {
    if (other == null) {
      return false;
    }
    return Objects.equals(title, other.title)
        && contextMode == other.contextMode
        && Objects.equals(contextSummaryTemplate, other.contextSummaryTemplate)
        && Objects.equals(objectiveTemplate, other.objectiveTemplate)
        && Objects.equals(callToActionLabel, other.callToActionLabel)
        && Objects.equals(validFrom, other.validFrom)
        && Objects.equals(validUntil, other.validUntil)
        && fieldSnapshot().equals(other.fieldSnapshot());
  }

  private List<String> fieldSnapshot() {
    List<String> snapshot = new ArrayList<>();
    for (ContextFieldDefinition field : contextFields) {
      snapshot.add(
          field.position()
              + "|"
              + field.key()
              + "|"
              + field.label()
              + "|"
              + field.type()
              + "|"
              + field.required()
              + "|"
              + field.source()
              + "|"
              + field.classification()
              + "|"
              + field.allowedValues());
    }
    return snapshot;
  }

  private static Set<String> placeholdersIn(String text) {
    Set<String> keys = new HashSet<>();
    Matcher matcher = PLACEHOLDER.matcher(text);
    while (matcher.find()) {
      keys.add(matcher.group(1));
    }
    return keys;
  }

  public String title() {
    return title;
  }

  public ContextMode contextMode() {
    return contextMode;
  }

  public String contextSummaryTemplate() {
    return contextSummaryTemplate;
  }

  public String objectiveTemplate() {
    return objectiveTemplate;
  }

  public String callToActionLabel() {
    return callToActionLabel;
  }

  public Instant validFrom() {
    return validFrom;
  }

  public Instant validUntil() {
    return validUntil;
  }

  public List<ContextFieldDefinition> contextFields() {
    return contextFields;
  }
}
