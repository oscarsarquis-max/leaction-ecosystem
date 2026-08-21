package br.com.banco.spider.governance.port;

import br.com.banco.spider.governance.GovernanceAuditEvent;
import java.util.List;

public interface GovernanceAuditStorePort {
  void append(GovernanceAuditEvent event);

  List<GovernanceAuditEvent> findByTargetRef(String targetRef, int limit);
}
