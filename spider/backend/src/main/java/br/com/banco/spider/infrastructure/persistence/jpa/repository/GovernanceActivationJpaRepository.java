package br.com.banco.spider.infrastructure.persistence.jpa.repository;

import br.com.banco.spider.infrastructure.persistence.jpa.entity.GovernanceActivationEntity;
import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;

public interface GovernanceActivationJpaRepository
    extends JpaRepository<GovernanceActivationEntity, String> {

  Optional<GovernanceActivationEntity> findByGovernanceScope(String governanceScope);
}
