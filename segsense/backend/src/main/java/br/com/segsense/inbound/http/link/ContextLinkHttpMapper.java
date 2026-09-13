package br.com.segsense.inbound.http.link;

import br.com.segsense.application.catalog.CatalogPageQuery;
import br.com.segsense.application.link.IssueContextLinkUseCase;
import br.com.segsense.domain.catalog.CatalogValidationException;
import br.com.segsense.domain.link.ContextLinkEvent;
import br.com.segsense.domain.link.InvalidPublisherContextException;
import br.com.segsense.domain.link.PublishedContextLink;
import br.com.segsense.domain.link.PublisherBindingDraft;
import br.com.segsense.domain.link.PublisherContextBinding;
import br.com.segsense.inbound.http.catalog.CatalogCollectionResponse;
import br.com.segsense.inbound.http.catalog.CatalogPageResponse;
import java.math.BigDecimal;
import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;

final class ContextLinkHttpMapper {

  private ContextLinkHttpMapper() {}

  static CatalogPageQuery pageQuery(Integer size, String after) {
    return CatalogPageQuery.of(size, after);
  }

  static List<PublisherBindingDraft> bindings(
      List<IssueContextLinkRequest.PublisherContextBindingRequest> raw) {
    if (raw == null) {
      return List.of();
    }
    if (raw.size() > 20) {
      throw new InvalidPublisherContextException();
    }
    List<PublisherBindingDraft> drafts = new ArrayList<>();
    for (IssueContextLinkRequest.PublisherContextBindingRequest item : raw) {
      if (item == null || item.fieldKey() == null || item.value() == null) {
        throw new InvalidPublisherContextException();
      }
      drafts.add(new PublisherBindingDraft(item.fieldKey(), typedValue(item.value())));
    }
    return List.copyOf(drafts);
  }

  static Instant expiresAt(Instant expiresAt) {
    if (expiresAt == null) {
      throw new CatalogValidationException("A expiração do link é obrigatória.");
    }
    return expiresAt;
  }

  static long expectedVersion(Long version) {
    if (version == null || version < 0) {
      throw new CatalogValidationException("A versão esperada é obrigatória.");
    }
    return version;
  }

  static IssuedContextLinkResponse issued(IssueContextLinkUseCase.IssuedContextLink issued) {
    PublishedContextLink link = issued.link();
    return new IssuedContextLinkResponse(
        link.id(),
        link.placementKey(),
        link.label(),
        link.status().name(),
        issued.effectiveStatus().name(),
        link.revisionNumber(),
        link.issuedAt(),
        link.issuedBy(),
        link.expiresAt(),
        link.version(),
        issued.rawToken(),
        issued.publicUrl(),
        link.tokenHint(),
        bindingsOf(link));
  }

  static ContextLinkResponse metadata(PublishedContextLink link, Instant now) {
    return new ContextLinkResponse(
        link.id(),
        link.placementKey(),
        link.label(),
        link.status().name(),
        link.effectiveStatus(now).name(),
        link.revisionNumber(),
        link.issuedAt(),
        link.issuedBy(),
        link.expiresAt(),
        link.revokedAt(),
        link.revokedBy(),
        link.revocationReason(),
        link.version(),
        link.tokenHint(),
        bindingsOf(link));
  }

  static ContextLinkEventResponse event(ContextLinkEvent event) {
    return new ContextLinkEventResponse(
        event.id(),
        event.eventType().name(),
        event.occurredAt(),
        event.actorSubject(),
        event.correlationId());
  }

  static <T> CatalogCollectionResponse<T> collection(List<T> items, CatalogPageResponse page) {
    return new CatalogCollectionResponse<>(items, page);
  }

  private static List<ContextLinkBindingResponse> bindingsOf(PublishedContextLink link) {
    List<ContextLinkBindingResponse> items = new ArrayList<>();
    for (PublisherContextBinding binding : link.bindings()) {
      items.add(
          new ContextLinkBindingResponse(
              binding.fieldKey(), binding.fieldType().name(), binding.publicValue()));
    }
    return List.copyOf(items);
  }

  private static Object typedValue(Object node) {
    if (node == null || node instanceof Map<?, ?> || node instanceof List<?>) {
      throw new InvalidPublisherContextException();
    }
    if (node instanceof Boolean flag) {
      return flag;
    }
    if (node instanceof BigDecimal decimal) {
      return decimal;
    }
    if (node instanceof Number number) {
      return new BigDecimal(number.toString());
    }
    if (node instanceof String text) {
      return text;
    }
    throw new InvalidPublisherContextException();
  }
}
