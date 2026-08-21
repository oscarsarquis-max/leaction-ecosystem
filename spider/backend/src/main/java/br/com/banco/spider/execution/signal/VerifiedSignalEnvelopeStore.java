package br.com.banco.spider.execution.signal;

import java.util.Map;
import java.util.Optional;
import java.util.concurrent.ConcurrentHashMap;
import org.springframework.stereotype.Component;

/** Armazenamento opaco de envelope verificado para aplicação assíncrona (memory). Sem MAC/nonce. */
@Component
public class VerifiedSignalEnvelopeStore {

  private final Map<String, ExternalSignalEnvelope> byPayloadRef = new ConcurrentHashMap<>();

  public String put(String payloadRef, ExternalSignalEnvelope envelope) {
    byPayloadRef.put(payloadRef, envelope);
    return payloadRef;
  }

  public Optional<ExternalSignalEnvelope> get(String payloadRef) {
    if (payloadRef == null) {
      return Optional.empty();
    }
    return Optional.ofNullable(byPayloadRef.get(payloadRef));
  }

  public void remove(String payloadRef) {
    if (payloadRef != null) {
      byPayloadRef.remove(payloadRef);
    }
  }
}
