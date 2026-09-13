package br.com.segsense.infrastructure.consent;

import java.util.List;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

interface ConsentNoticeSnapshotSpringRepository
    extends JpaRepository<ConsentNoticeSnapshotJpaEntity, UUID> {

  List<ConsentNoticeSnapshotJpaEntity> findByNoticeIdOrderByVersionNumberAsc(UUID noticeId);
}
