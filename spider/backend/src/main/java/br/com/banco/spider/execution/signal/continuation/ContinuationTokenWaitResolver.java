package br.com.banco.spider.execution.signal.continuation;

import br.com.banco.spider.execution.persistence.port.ExecutionWaitStorePort;
import br.com.banco.spider.execution.wait.ExecutionWaitRecord;
import br.com.banco.spider.execution.wait.WaitState;
import java.time.Instant;
import java.util.Optional;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import reactor.core.publisher.Mono;
import reactor.core.scheduler.Schedulers;

@Service
public class ContinuationTokenWaitResolver {

  private static final Logger log = LoggerFactory.getLogger(ContinuationTokenWaitResolver.class);

  private final ExecutionWaitStorePort waitStore;
  private final ContinuationTokenFingerprintService fingerprintService;
  private final boolean tokenEnabled;
  private final boolean legacyLookupEnabled;

  public ContinuationTokenWaitResolver(
      ExecutionWaitStorePort waitStore,
      ContinuationTokenFingerprintService fingerprintService,
      @Value("${spider.signal.continuation-token.enabled:false}") boolean tokenEnabled,
      @Value("${spider.signal.continuation-token.legacy-lookup-enabled:true}")
          boolean legacyLookupEnabled) {
    this.waitStore = waitStore;
    this.fingerprintService = fingerprintService;
    this.tokenEnabled = tokenEnabled;
    this.legacyLookupEnabled = legacyLookupEnabled;
  }

  public Mono<Optional<ExecutionWaitRecord>> resolveByToken(String rawToken, Instant now) {
    if (!tokenEnabled) {
      return Mono.just(Optional.empty());
    }
    return Mono.<Optional<ExecutionWaitRecord>>fromCallable(
            () -> {
              ContinuationToken token;
              try {
                token = ContinuationToken.parse(rawToken);
              } catch (IllegalArgumentException ex) {
                log.info("event=token_lookup_normalized_failure reasonCode=MALFORMED");
                return Optional.empty();
              }
              ContinuationTokenFingerprint fp = fingerprintService.legacySha(token);
              token.zeroize();
              Optional<ExecutionWaitRecord> found =
                  waitStore.findByContinuationTokenFingerprint(fp.digest());
              if (found.isEmpty()) {
                log.info("event=token_lookup_normalized_failure reasonCode=NOT_FOUND");
                return Optional.empty();
              }
              ExecutionWaitRecord wait = found.get();
              if (wait.state() != WaitState.WAITING && wait.state() != WaitState.RESUMING) {
                log.info("event=token_lookup_normalized_failure reasonCode=TERMINAL");
                return Optional.empty();
              }
              if (!wait.expiresAt().isAfter(now)
                  || (wait.continuationTokenExpiresAt() != null
                      && !wait.continuationTokenExpiresAt().isAfter(now))) {
                log.info("event=token_lookup_normalized_failure reasonCode=EXPIRED");
                return Optional.empty();
              }
              log.info("event=token_lookup_success reasonCode=OK");
              return Optional.of(wait);
            })
        .subscribeOn(Schedulers.boundedElastic());
  }

  public boolean legacyLookupEnabled() {
    return legacyLookupEnabled;
  }
}
