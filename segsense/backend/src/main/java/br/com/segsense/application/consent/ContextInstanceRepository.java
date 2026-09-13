package br.com.segsense.application.consent;

import br.com.segsense.domain.consent.ConsentDecision;
import br.com.segsense.domain.consent.ContextInstance;
import java.util.Optional;

public interface ContextInstanceRepository {

  ContextInstance saveNew(ContextInstance instance);

  ContextInstance saveValues(ContextInstance instance);

  ContextInstance saveDecision(ContextInstance instance, ConsentDecision decision);

  Optional<ContextInstance> findByCredentialDigest(byte[] digest);

  Optional<ContextInstance> findByIdempotencyKeyDigest(byte[] digest);
}
