package br.com.banco.spider.execution.signal;

import br.com.banco.spider.execution.wait.ExecutionWaitRecord;
import br.com.banco.spider.execution.wait.WaitState;
import org.springframework.stereotype.Service;

@Service
public class ExternalSignalDispositionService {

  public ExternalSignalIngressOutcome classifyLateOrOrphan(
      ExecutionWaitRecord wait, LateSignalPolicy policy) {
    if (wait == null) {
      return ExternalSignalIngressOutcome.ORPHAN;
    }
    if (wait.state() == WaitState.EXPIRED
        || wait.state() == WaitState.RESUMED
        || wait.state() == WaitState.CANCELLED) {
      return switch (policy == null ? LateSignalPolicy.RECORD_ONLY : policy) {
        case IGNORE -> ExternalSignalIngressOutcome.LATE;
        case RECORD_ONLY -> ExternalSignalIngressOutcome.LATE;
        case MANUAL_REVIEW -> ExternalSignalIngressOutcome.LATE;
      };
    }
    return ExternalSignalIngressOutcome.ACCEPTED_PENDING_APPLICATION;
  }
}
