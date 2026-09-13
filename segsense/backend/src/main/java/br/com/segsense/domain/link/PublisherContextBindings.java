package br.com.segsense.domain.link;

import br.com.segsense.domain.catalog.CatalogValidationException;
import br.com.segsense.domain.opportunity.ContextFieldDefinition;
import br.com.segsense.domain.opportunity.ContextFieldSource;
import br.com.segsense.domain.opportunity.ContextFieldType;
import br.com.segsense.domain.opportunity.ContextMode;
import br.com.segsense.domain.opportunity.OpportunityContent;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.UUID;
import java.util.function.Function;
import java.util.stream.Collectors;

public final class PublisherContextBindings {

  public static final int MAX_BINDINGS = 20;

  private PublisherContextBindings() {}

  public static List<PublisherContextBinding> parse(
      OpportunityContent content, List<PublisherBindingDraft> drafts) {
    if (content.contextMode() == ContextMode.STATIC) {
      if (drafts != null && !drafts.isEmpty()) {
        throw new InvalidPublisherContextException();
      }
      return List.of();
    }
    List<PublisherBindingDraft> inputs = drafts == null ? List.of() : drafts;
    if (inputs.size() > MAX_BINDINGS) {
      throw new InvalidPublisherContextException();
    }
    Map<String, ContextFieldDefinition> declared =
        content.contextFields().stream()
            .collect(Collectors.toMap(ContextFieldDefinition::key, Function.identity()));
    Set<String> seen = new HashSet<>();
    List<PublisherContextBinding> bindings = new ArrayList<>();
    for (PublisherBindingDraft draft : inputs) {
      if (!seen.add(draft.fieldKey())) {
        throw new InvalidPublisherContextException();
      }
      ContextFieldDefinition field = declared.get(draft.fieldKey());
      if (field == null) {
        throw new InvalidPublisherContextException();
      }
      if (field.source() == ContextFieldSource.USER) {
        throw new InvalidPublisherContextException();
      }
      if (field.source() != ContextFieldSource.PUBLISHER
          && field.source() != ContextFieldSource.EITHER) {
        throw new InvalidPublisherContextException();
      }
      bindings.add(bind(field, draft));
    }
    for (ContextFieldDefinition field : content.contextFields()) {
      if (field.required()
          && field.source() == ContextFieldSource.PUBLISHER
          && bindings.stream().noneMatch(binding -> binding.fieldKey().equals(field.key()))) {
        throw new RequiredPublisherContextMissingException();
      }
    }
    return List.copyOf(bindings);
  }

  private static PublisherContextBinding bind(
      ContextFieldDefinition field, PublisherBindingDraft draft) {
    try {
      if (looksLikeSerializedJson(draft)) {
        throw new InvalidPublisherContextException();
      }
      return switch (field.type()) {
        case TEXT, ENUM -> {
          if (!draft.isText()) {
            throw new InvalidPublisherContextException();
          }
          yield PublisherContextBinding.text(UUID.randomUUID(), field, draft.text());
        }
        case NUMBER -> {
          if (!draft.isNumber()) {
            throw new InvalidPublisherContextException();
          }
          yield PublisherContextBinding.number(UUID.randomUUID(), field, draft.number());
        }
        case BOOLEAN -> {
          if (!draft.isBoolean()) {
            throw new InvalidPublisherContextException();
          }
          yield PublisherContextBinding.bool(UUID.randomUUID(), field, draft.bool());
        }
        case DATE -> {
          if (!draft.isText()) {
            throw new InvalidPublisherContextException();
          }
          yield PublisherContextBinding.date(UUID.randomUUID(), field, draft.text());
        }
      };
    } catch (CatalogValidationException exception) {
      throw new InvalidPublisherContextException();
    }
  }

  private static boolean looksLikeSerializedJson(PublisherBindingDraft draft) {
    if (!draft.isText()) {
      return false;
    }
    String text = draft.text().trim();
    return text.startsWith("{") || text.startsWith("[");
  }
}
