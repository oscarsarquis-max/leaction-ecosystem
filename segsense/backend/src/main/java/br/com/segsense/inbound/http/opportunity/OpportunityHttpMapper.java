package br.com.segsense.inbound.http.opportunity;

import br.com.segsense.application.catalog.CatalogPageQuery;
import br.com.segsense.application.opportunity.OpportunityGovernanceView;
import br.com.segsense.domain.catalog.CatalogValidationException;
import br.com.segsense.domain.opportunity.ContextFieldDefinition;
import br.com.segsense.domain.opportunity.ContextFieldSource;
import br.com.segsense.domain.opportunity.ContextFieldType;
import br.com.segsense.domain.opportunity.ContextMode;
import br.com.segsense.domain.opportunity.ContextualOpportunity;
import br.com.segsense.domain.opportunity.FieldClassification;
import br.com.segsense.domain.opportunity.GovernanceAction;
import br.com.segsense.domain.opportunity.LifecycleEvent;
import br.com.segsense.domain.opportunity.OpportunityContent;
import br.com.segsense.domain.opportunity.OpportunityDecision;
import br.com.segsense.domain.opportunity.OpportunityRevision;
import java.time.Instant;
import java.time.format.DateTimeParseException;
import java.util.ArrayList;
import java.util.List;
import java.util.Locale;

final class OpportunityHttpMapper {

  private OpportunityHttpMapper() {}

  static CatalogPageQuery pageQuery(Integer size, String after) {
    return CatalogPageQuery.of(size, after);
  }

  static long expectedVersion(Long version) {
    if (version == null || version < 0) {
      throw new CatalogValidationException("A versão esperada é obrigatória.");
    }
    return version;
  }

  static int baseRevision(Integer revision) {
    if (revision == null || revision < 1) {
      throw new CatalogValidationException("A revisão de base é obrigatória.");
    }
    return revision;
  }

  static OpportunityContent content(
      String title,
      String contextMode,
      String contextSummaryTemplate,
      String objectiveTemplate,
      String callToActionLabel,
      String validFrom,
      String validUntil,
      List<ContextFieldRequest> fields) {
    return OpportunityContent.parse(
        title,
        contextMode(contextMode),
        contextSummaryTemplate,
        objectiveTemplate,
        callToActionLabel,
        instant(validFrom),
        instant(validUntil),
        contextFields(fields));
  }

  static int revisionNumber(Integer revision) {
    if (revision == null || revision < 1) {
      throw new CatalogValidationException("A revisão da submissão é obrigatória.");
    }
    return revision;
  }

  static OpportunityResponse opportunity(
      ContextualOpportunity opportunity,
      boolean effectivelyAvailable,
      boolean effectivelyPublishable,
      boolean effectivelyPublished) {
    return new OpportunityResponse(
        opportunity.id(),
        opportunity.publisherId(),
        opportunity.channelId(),
        opportunity.environmentId(),
        opportunity.key().value(),
        opportunity.status().name(),
        opportunity.currentRevision(),
        opportunity.submittedRevision(),
        opportunity.approvedRevision(),
        opportunity.version(),
        opportunity.createdAt(),
        opportunity.updatedAt(),
        opportunity.createdBy(),
        opportunity.updatedBy(),
        effectivelyAvailable,
        effectivelyPublishable,
        effectivelyPublished,
        snapshot(opportunity.current()));
  }

  static OpportunityGovernanceResponse governance(OpportunityGovernanceView view) {
    OpportunityDecision decision = view.latestDecision();
    return new OpportunityGovernanceResponse(
        view.opportunity().id(),
        view.opportunity().status().name(),
        view.opportunity().currentRevision(),
        view.opportunity().submittedRevision(),
        view.opportunity().approvedRevision(),
        view.opportunity().openSubmissionId(),
        view.opportunity().submittedBy(),
        view.opportunity().approvedBy(),
        view.opportunity().version(),
        view.effectivelyAvailable(),
        view.effectivelyPublishable(),
        view.effectivelyPublished(),
        view.windowOpen(),
        view.windowExpired(),
        "INTERNAL_AUTHORIZATION_ONLY",
        decision == null
            ? null
            : new OpportunityGovernanceResponse.DecisionSnapshot(
                decision.id(),
                decision.submissionId(),
                decision.revisionNumber(),
                decision.outcome().name(),
                decision.decidedAt(),
                decision.decidedBy(),
                decision.justification()),
        view.availableActions().stream().map(GovernanceAction::name).toList());
  }

  static LifecycleEventResponse event(LifecycleEvent event) {
    return new LifecycleEventResponse(
        event.id(),
        event.opportunityId(),
        event.revisionNumber(),
        event.type().name(),
        event.previousStatus().name(),
        event.newStatus().name(),
        event.actorSubjectId(),
        event.occurredAt(),
        event.justification(),
        event.correlationId());
  }

  static OpportunityRevisionSnapshotResponse snapshot(OpportunityRevision revision) {
    OpportunityContent content = revision.content();
    List<ContextFieldResponse> fields = new ArrayList<>();
    for (ContextFieldDefinition field : content.contextFields()) {
      fields.add(
          new ContextFieldResponse(
              field.key(),
              field.label(),
              field.type().name(),
              field.required(),
              field.source().name(),
              field.classification().name(),
              field.position(),
              field.allowedValues()));
    }
    return new OpportunityRevisionSnapshotResponse(
        revision.id(),
        revision.revisionNumber(),
        revision.createdAt(),
        revision.createdBy(),
        content.title(),
        content.contextMode().name(),
        content.contextSummaryTemplate(),
        content.objectiveTemplate(),
        content.callToActionLabel(),
        content.validFrom(),
        content.validUntil(),
        List.copyOf(fields));
  }

  private static ContextMode contextMode(String raw) {
    if (raw == null || raw.isBlank()) {
      throw new CatalogValidationException("O modo de contexto é obrigatório.");
    }
    try {
      return ContextMode.valueOf(raw.trim().toUpperCase(Locale.ROOT));
    } catch (IllegalArgumentException ex) {
      throw new CatalogValidationException("O modo de contexto informado é inválido.");
    }
  }

  private static Instant instant(String raw) {
    if (raw == null || raw.isBlank()) {
      return null;
    }
    try {
      return Instant.parse(raw.trim());
    } catch (DateTimeParseException ex) {
      throw new CatalogValidationException("A data informada deve estar em UTC ISO-8601.");
    }
  }

  private static List<ContextFieldDefinition> contextFields(List<ContextFieldRequest> raw) {
    if (raw == null || raw.isEmpty()) {
      return List.of();
    }
    List<ContextFieldDefinition> fields = new ArrayList<>();
    int position = 0;
    for (ContextFieldRequest field : raw) {
      if (field == null) {
        throw new CatalogValidationException("A definição do campo é obrigatória.");
      }
      fields.add(
          ContextFieldDefinition.parse(
              field.key(),
              field.label(),
              fieldType(field.type()),
              Boolean.TRUE.equals(field.required()),
              fieldSource(field.source()),
              fieldClassification(field.classification()),
              field.allowedValues(),
              position));
      position++;
    }
    return List.copyOf(fields);
  }

  private static ContextFieldType fieldType(String raw) {
    if (raw == null || raw.isBlank()) {
      throw new CatalogValidationException("O tipo do campo é obrigatório.");
    }
    try {
      return ContextFieldType.valueOf(raw.trim().toUpperCase(Locale.ROOT));
    } catch (IllegalArgumentException ex) {
      throw new CatalogValidationException("O tipo do campo informado é inválido.");
    }
  }

  private static ContextFieldSource fieldSource(String raw) {
    if (raw == null || raw.isBlank()) {
      throw new CatalogValidationException("A origem do campo é obrigatória.");
    }
    try {
      return ContextFieldSource.valueOf(raw.trim().toUpperCase(Locale.ROOT));
    } catch (IllegalArgumentException ex) {
      throw new CatalogValidationException("A origem do campo informada é inválida.");
    }
  }

  private static FieldClassification fieldClassification(String raw) {
    if (raw == null || raw.isBlank()) {
      return FieldClassification.NON_PERSONAL;
    }
    try {
      return FieldClassification.valueOf(raw.trim().toUpperCase(Locale.ROOT));
    } catch (IllegalArgumentException ex) {
      throw new CatalogValidationException("A classificação do campo informada é inválida.");
    }
  }
}
