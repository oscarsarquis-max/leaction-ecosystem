package br.com.banco.spider.infrastructure.persistence.jpa.repository;

import br.com.banco.spider.execution.inbox.InboxProcessingState;
import br.com.banco.spider.infrastructure.persistence.jpa.entity.InboxMessageEntity;
import java.util.List;
import org.springframework.data.jpa.repository.JpaRepository;

public interface InboxMessageJpaRepository
    extends JpaRepository<InboxMessageEntity, InboxMessageEntity.Pk> {

  List<InboxMessageEntity> findByProcessingState(InboxProcessingState state);
}
