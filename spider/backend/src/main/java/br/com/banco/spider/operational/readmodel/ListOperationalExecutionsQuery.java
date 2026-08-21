package br.com.banco.spider.operational.readmodel;

import br.com.banco.spider.execution.domain.ExecutionState;
import java.time.Instant;
import java.util.List;

public record ListOperationalExecutionsQuery(
    List<ExecutionState> states,
    String routeCode,
    Instant startedFrom,
    Instant startedTo,
    boolean onlyWaiting,
    Instant cursorStartedAt,
    String cursorExecutionId,
    int limit) {}
