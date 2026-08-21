package br.com.banco.spider.infrastructure.persistence.jpa.repository;

import br.com.banco.spider.infrastructure.persistence.jpa.entity.ExecutionStepEntity;
import org.springframework.data.jpa.repository.JpaRepository;

public interface ExecutionStepJpaRepository
    extends JpaRepository<ExecutionStepEntity, ExecutionStepEntity.Pk> {}
