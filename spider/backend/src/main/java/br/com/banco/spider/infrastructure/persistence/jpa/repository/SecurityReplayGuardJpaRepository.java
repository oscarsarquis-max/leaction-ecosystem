package br.com.banco.spider.infrastructure.persistence.jpa.repository;

import br.com.banco.spider.infrastructure.persistence.jpa.entity.SecurityReplayGuardEntity;
import java.time.Instant;
import java.util.List;
import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface SecurityReplayGuardJpaRepository
    extends JpaRepository<SecurityReplayGuardEntity, String> {

  Optional<SecurityReplayGuardEntity> findByReplayScopeHashAndNonceHashAndFingerprintVersion(
      String replayScopeHash, String nonceHash, String fingerprintVersion);

  @Query(
      """
      select e from SecurityReplayGuardEntity e
      where e.expiresAt <= :now
      order by e.expiresAt asc
      """)
  List<SecurityReplayGuardEntity> findExpired(@Param("now") Instant now);
}
