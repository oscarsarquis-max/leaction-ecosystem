package br.com.segsense.infrastructure.consent;

import java.util.List;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

interface ContextInstanceValueSpringRepository
    extends JpaRepository<ContextInstanceValueJpaEntity, UUID> {

  List<ContextInstanceValueJpaEntity> findByInstanceIdOrderByFieldKeyAsc(UUID instanceId);

  void deleteByInstanceId(UUID instanceId);
}
