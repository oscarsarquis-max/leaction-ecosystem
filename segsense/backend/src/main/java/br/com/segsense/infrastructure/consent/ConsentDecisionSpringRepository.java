package br.com.segsense.infrastructure.consent;

import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

interface ConsentDecisionSpringRepository extends JpaRepository<ConsentDecisionJpaEntity, UUID> {}
