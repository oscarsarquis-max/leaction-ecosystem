package br.com.segsense.infrastructure.demo;

import java.util.Optional;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

interface DemoProtectionJourneySpringRepository
    extends JpaRepository<DemoProtectionJourneyJpaEntity, UUID> {

  Optional<DemoProtectionJourneyJpaEntity> findByIdempotencyKeyHash(String hash);
}
