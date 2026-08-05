package br.com.banco.spider.repository;

import br.com.banco.spider.model.AuditTrace;
import java.util.List;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

public interface AuditTraceRepository extends JpaRepository<AuditTrace, UUID> {

  List<AuditTrace> findTop50ByOrderByStartedAtDesc();

  List<AuditTrace> findByCorrelationId(UUID correlationId);
}
