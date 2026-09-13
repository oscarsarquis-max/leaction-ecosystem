package br.com.segsense.infrastructure.opportunity;

import java.util.List;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

interface OpportunityRevisionFieldSpringRepository
    extends JpaRepository<OpportunityRevisionFieldJpaEntity, UUID> {

  List<OpportunityRevisionFieldJpaEntity> findByOpportunityRevisionIdOrderByPositionAsc(
      UUID opportunityRevisionId);
}
