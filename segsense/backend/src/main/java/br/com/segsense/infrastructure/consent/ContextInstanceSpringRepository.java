package br.com.segsense.infrastructure.consent;

import java.util.Optional;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

interface ContextInstanceSpringRepository extends JpaRepository<ContextInstanceJpaEntity, UUID> {

  Optional<ContextInstanceJpaEntity> findByCredentialDigest(byte[] credentialDigest);

  Optional<ContextInstanceJpaEntity> findByIdempotencyKeyDigest(byte[] idempotencyKeyDigest);
}
