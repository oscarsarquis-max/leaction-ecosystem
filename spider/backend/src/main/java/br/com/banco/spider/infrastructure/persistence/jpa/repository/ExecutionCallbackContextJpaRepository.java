package br.com.banco.spider.infrastructure.persistence.jpa.repository;

import br.com.banco.spider.infrastructure.persistence.jpa.entity.ExecutionCallbackContextEntity;
import org.springframework.data.jpa.repository.JpaRepository;

public interface ExecutionCallbackContextJpaRepository
    extends JpaRepository<ExecutionCallbackContextEntity, String> {}
