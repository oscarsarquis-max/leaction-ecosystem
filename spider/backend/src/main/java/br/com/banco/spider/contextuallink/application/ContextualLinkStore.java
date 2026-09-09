package br.com.banco.spider.contextuallink.application;

import br.com.banco.spider.contextuallink.domain.ContextualLinkSession;
import java.util.Optional;

public interface ContextualLinkStore {
  void save(ContextualLinkSession session);

  Optional<ContextualLinkSession> findByContextId(String contextId);

  Optional<ContextualLinkSession> findByClickId(String clickId);
}
