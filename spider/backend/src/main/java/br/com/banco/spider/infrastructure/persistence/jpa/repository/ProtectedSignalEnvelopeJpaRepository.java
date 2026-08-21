package br.com.banco.spider.infrastructure.persistence.jpa.repository;

import br.com.banco.spider.execution.signal.protection.ProtectedEnvelopeState;
import br.com.banco.spider.infrastructure.persistence.jpa.entity.ProtectedSignalEnvelopeEntity;
import java.util.List;
import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;

public interface ProtectedSignalEnvelopeJpaRepository
    extends JpaRepository<ProtectedSignalEnvelopeEntity, String> {

  Optional<ProtectedSignalEnvelopeEntity> findByInboxLogicalKey(String inboxLogicalKey);

  List<ProtectedSignalEnvelopeEntity> findByState(ProtectedEnvelopeState state);
}
