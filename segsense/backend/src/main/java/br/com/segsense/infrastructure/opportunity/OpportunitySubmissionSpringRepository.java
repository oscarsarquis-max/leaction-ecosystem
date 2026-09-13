package br.com.segsense.infrastructure.opportunity;

import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

interface OpportunitySubmissionSpringRepository
    extends JpaRepository<OpportunitySubmissionJpaEntity, UUID> {}
