package br.com.segsense.infrastructure.consent;

import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

interface ConsentNoticeSpringRepository extends JpaRepository<ConsentNoticeJpaEntity, UUID> {

  Optional<ConsentNoticeJpaEntity> findByPublisherIdAndChannelIdAndEnvironmentIdAndOpportunityId(
      UUID publisherId, UUID channelId, UUID environmentId, UUID opportunityId);

  Optional<ConsentNoticeJpaEntity> findByOpportunityRevisionIdAndStatus(
      UUID opportunityRevisionId, String status);
}
