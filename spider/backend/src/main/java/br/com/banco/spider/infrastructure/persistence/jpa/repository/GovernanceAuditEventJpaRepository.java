package br.com.banco.spider.infrastructure.persistence.jpa.repository;

import br.com.banco.spider.infrastructure.persistence.jpa.entity.GovernanceAuditEventEntity;
import java.util.List;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;

public interface GovernanceAuditEventJpaRepository
    extends JpaRepository<GovernanceAuditEventEntity, String> {

  List<GovernanceAuditEventEntity> findByTargetRefOrderByOccurredAtDesc(
      String targetRef, Pageable pageable);
}
