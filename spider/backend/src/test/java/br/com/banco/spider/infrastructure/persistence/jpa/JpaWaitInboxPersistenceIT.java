package br.com.banco.spider.infrastructure.persistence.jpa;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import br.com.banco.spider.execution.inbox.InboxProcessingState;
import br.com.banco.spider.execution.inbox.InboxRecord;
import br.com.banco.spider.execution.inbox.InboxReservationStatus;
import br.com.banco.spider.execution.inbox.InboxValidationState;
import br.com.banco.spider.execution.wait.ExecutionWaitRecord;
import br.com.banco.spider.execution.wait.WaitState;
import br.com.banco.spider.execution.wait.WaitType;
import br.com.banco.spider.infrastructure.persistence.jpa.entity.ExecutionWaitEntity;
import br.com.banco.spider.infrastructure.persistence.jpa.entity.InboxMessageEntity;
import br.com.banco.spider.infrastructure.persistence.jpa.repository.ExecutionWaitJpaRepository;
import br.com.banco.spider.infrastructure.persistence.jpa.repository.InboxMessageJpaRepository;
import java.time.Instant;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.autoconfigure.domain.EntityScan;
import org.springframework.boot.test.autoconfigure.jdbc.AutoConfigureTestDatabase;
import org.springframework.boot.test.autoconfigure.orm.jpa.DataJpaTest;
import org.springframework.data.jpa.repository.config.EnableJpaRepositories;
import org.springframework.test.context.TestPropertySource;

@DataJpaTest
@AutoConfigureTestDatabase(replace = AutoConfigureTestDatabase.Replace.ANY)
@EntityScan({
  "br.com.banco.spider.infrastructure.persistence.jpa.entity",
  "br.com.banco.spider.model"
})
@EnableJpaRepositories({
  "br.com.banco.spider.infrastructure.persistence.jpa.repository",
  "br.com.banco.spider.repository"
})
@TestPropertySource(
    properties = {
      "spring.datasource.url=jdbc:h2:mem:spider_wait_inbox;MODE=PostgreSQL;DB_CLOSE_DELAY=-1",
      "spring.datasource.driver-class-name=org.h2.Driver",
      "spring.datasource.username=sa",
      "spring.datasource.password=",
      "spring.jpa.hibernate.ddl-auto=create-drop",
      "spring.jpa.database-platform=org.hibernate.dialect.H2Dialect",
      "spider.canonical.persistence.mode=jpa"
    })
class JpaWaitInboxPersistenceIT {

  @Autowired ExecutionWaitJpaRepository waitRepo;
  @Autowired InboxMessageJpaRepository inboxRepo;

  @Test
  void waitAndInboxPersistAsStrings() {
    Instant now = Instant.parse("2026-07-21T12:00:00Z");
    ExecutionWaitEntity w = new ExecutionWaitEntity();
    w.setWaitId("wait-1");
    w.setExecutionId("e1");
    w.setStepId("s1");
    w.setAttemptId("a1");
    w.setWaitType(WaitType.ASYNC_COMPLETION);
    w.setWaitPolicyRef("policy:wait:default-async@1.0");
    w.setState(WaitState.WAITING);
    w.setStateVersion(0);
    w.setCreatedAt(now);
    w.setExpiresAt(now.plusSeconds(60));
    waitRepo.save(w);

    InboxMessageEntity i = new InboxMessageEntity();
    i.setSourceRef("source:mock-async@1.0");
    i.setMessageId("m1");
    i.setBindingRef("binding:mock-universal@1.0");
    i.setContractRef("contract:signal:async-completion@1.0");
    i.setDeduplicationKeyHash("dedup");
    i.setMessageFingerprint("fp1");
    i.setFingerprintVersion("1.0");
    i.setReceivedAt(now);
    i.setValidationState(InboxValidationState.RECEIVED);
    i.setProcessingState(InboxProcessingState.PENDING);
    i.setExpiresAt(now.plusSeconds(60));
    inboxRepo.save(i);

    assertEquals(WaitState.WAITING, waitRepo.findById("wait-1").orElseThrow().getState());
    assertTrue(inboxRepo.findById(new InboxMessageEntity.Pk("source:mock-async@1.0", "m1")).isPresent());

    JpaExecutionWaitStoreAdapter waitAdapter = new JpaExecutionWaitStoreAdapter(waitRepo);
    JpaInboxStoreAdapter inboxAdapter = new JpaInboxStoreAdapter(inboxRepo);
    assertTrue(waitAdapter.findByWaitId("wait-1").isPresent());
    var reserved =
        inboxAdapter.reserve(
            new InboxRecord(
                "m2",
                "source:mock-async@1.0",
                "binding:x",
                "contract:c",
                "d",
                "fp2",
                "1.0",
                "e1",
                "s1",
                null,
                now,
                InboxValidationState.RECEIVED,
                InboxProcessingState.PENDING,
                null,
                null,
                now.plusSeconds(60)));
    assertEquals(InboxReservationStatus.RESERVED_NEW, reserved.status());
  }
}
