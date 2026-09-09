package br.com.banco.spider.contextuallink.application;

import br.com.banco.spider.contextuallink.domain.ContextualLinkSession;
import java.util.Optional;
import java.util.concurrent.ConcurrentHashMap;

public final class InMemoryContextualLinkStore implements ContextualLinkStore {

  private final ConcurrentHashMap<String, ContextualLinkSession> byContext = new ConcurrentHashMap<>();
  private final ConcurrentHashMap<String, String> clickToContext = new ConcurrentHashMap<>();

  @Override
  public void save(ContextualLinkSession session) {
    byContext.put(session.click().contextId(), session);
    clickToContext.put(session.click().clickId(), session.click().contextId());
  }

  @Override
  public Optional<ContextualLinkSession> findByContextId(String contextId) {
    if (contextId == null || contextId.isBlank()) {
      return Optional.empty();
    }
    return Optional.ofNullable(byContext.get(contextId));
  }

  @Override
  public Optional<ContextualLinkSession> findByClickId(String clickId) {
    if (clickId == null || clickId.isBlank()) {
      return Optional.empty();
    }
    String contextId = clickToContext.get(clickId);
    return contextId == null ? Optional.empty() : findByContextId(contextId);
  }
}
