package br.com.banco.spider.infrastructure.persistence.jpa.repository;

import br.com.banco.spider.infrastructure.persistence.jpa.entity.GovernanceActivationHistoryEntity;
import java.util.List;
import org.springframework.data.jpa.repository.JpaRepository;

public interface GovernanceActivationHistoryJpaRepository
    extends JpaRepository<GovernanceActivationHistoryEntity, Long> {

  List<GovernanceActivationHistoryEntity>
      findByGovernanceScopeOrderByActivationSequenceDesc(String governanceScope);
}
