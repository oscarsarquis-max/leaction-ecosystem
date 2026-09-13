package br.com.segsense.infrastructure.demo;

import br.com.segsense.application.demo.DemoProtectionJourneyRepository;
import br.com.segsense.domain.demo.DemoProtectionJourney;
import java.util.Optional;
import java.util.UUID;
import org.springframework.stereotype.Repository;

@Repository
public class JpaDemoProtectionJourneyRepository implements DemoProtectionJourneyRepository {

  private final DemoProtectionJourneySpringRepository spring;

  public JpaDemoProtectionJourneyRepository(DemoProtectionJourneySpringRepository spring) {
    this.spring = spring;
  }

  @Override
  public DemoProtectionJourney save(DemoProtectionJourney journey) {
    DemoProtectionJourneyJpaEntity entity =
        spring.findById(journey.id()).orElseGet(DemoProtectionJourneyJpaEntity::new);
    entity.setId(journey.id());
    entity.setScenarioKey(journey.scenarioKey());
    entity.setDeclaredObjective(journey.declaredObjective());
    entity.setStatus(journey.status());
    entity.setCorrelationId(journey.correlationId());
    entity.setIdempotencyKeyHash(journey.idempotencyKeyHash());
    entity.setSpiderDecisionId(journey.spiderDecisionId());
    entity.setMockResultId(journey.mockResultId());
    entity.setFailureKind(journey.failureKind());
    entity.setProjectionJson(journey.projectionJson());
    entity.setCreatedAt(journey.createdAt());
    entity.setUpdatedAt(journey.updatedAt());
    spring.saveAndFlush(entity);
    return journey;
  }

  @Override
  public Optional<DemoProtectionJourney> findById(UUID id) {
    return spring.findById(id).map(JpaDemoProtectionJourneyRepository::toDomain);
  }

  @Override
  public Optional<DemoProtectionJourney> findByIdempotencyKeyHash(String hash) {
    return spring.findByIdempotencyKeyHash(hash).map(JpaDemoProtectionJourneyRepository::toDomain);
  }

  private static DemoProtectionJourney toDomain(DemoProtectionJourneyJpaEntity entity) {
    return new DemoProtectionJourney(
        entity.getId(),
        entity.getScenarioKey(),
        entity.getDeclaredObjective(),
        entity.getStatus(),
        entity.getCorrelationId(),
        entity.getIdempotencyKeyHash(),
        entity.getSpiderDecisionId(),
        entity.getMockResultId(),
        entity.getFailureKind(),
        entity.getProjectionJson(),
        entity.getCreatedAt(),
        entity.getUpdatedAt());
  }
}
