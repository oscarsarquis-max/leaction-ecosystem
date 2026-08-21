package br.com.banco.spider.execution.signal.protection;

import java.util.EnumMap;
import java.util.Map;
import org.springframework.stereotype.Service;

/** Health summary sem ciphertext/IV/payload — deny-by-default (sem Controller). */
@Service
public class ProtectedSignalEnvelopeHealthService {

  private final ProtectedSignalEnvelopeStorePort store;

  public ProtectedSignalEnvelopeHealthService(ProtectedSignalEnvelopeStorePort store) {
    this.store = store;
  }

  public Map<ProtectedEnvelopeState, Integer> countsByState() {
    Map<ProtectedEnvelopeState, Integer> out = new EnumMap<>(ProtectedEnvelopeState.class);
    for (ProtectedEnvelopeState s : ProtectedEnvelopeState.values()) {
      out.put(s, store.findByState(s).size());
    }
    return out;
  }
}
