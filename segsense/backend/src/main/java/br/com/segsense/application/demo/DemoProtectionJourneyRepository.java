package br.com.segsense.application.demo;

import br.com.segsense.domain.demo.DemoProtectionJourney;
import java.util.Optional;
import java.util.UUID;

public interface DemoProtectionJourneyRepository {

  DemoProtectionJourney save(DemoProtectionJourney journey);

  Optional<DemoProtectionJourney> findById(UUID id);

  Optional<DemoProtectionJourney> findByIdempotencyKeyHash(String hash);
}
