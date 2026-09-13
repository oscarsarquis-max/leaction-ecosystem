package br.com.segsense.infrastructure.consent;

import java.util.List;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

interface ConsentNoticeFieldSpringRepository
    extends JpaRepository<ConsentNoticeFieldJpaEntity, UUID> {

  List<ConsentNoticeFieldJpaEntity> findBySnapshotIdOrderByPositionAsc(UUID snapshotId);
}
