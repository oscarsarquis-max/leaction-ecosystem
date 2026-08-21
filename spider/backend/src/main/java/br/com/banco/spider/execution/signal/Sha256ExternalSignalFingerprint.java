package br.com.banco.spider.execution.signal;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.HexFormat;
import org.springframework.stereotype.Component;

@Component
public class Sha256ExternalSignalFingerprint
    implements ExternalSignalFingerprintPort, InboxDeduplicationKeyPort {

  private static final String VERSION = "1.0";

  @Override
  public String fingerprintVersion() {
    return VERSION;
  }

  @Override
  public String fingerprint(ExternalSignalEnvelope signal) {
    StringBuilder sb = new StringBuilder();
    sb.append("source=").append(signal.sourceRef()).append('\n');
    sb.append("messageId=").append(signal.messageId()).append('\n');
    sb.append("contract=").append(signal.contractRef()).append('\n');
    sb.append("executionId=").append(signal.executionId()).append('\n');
    sb.append("stepId=").append(signal.stepId()).append('\n');
    sb.append("extOp=")
        .append(signal.externalOperationRef() == null ? "" : signal.externalOperationRef())
        .append('\n');
    sb.append("disposition=").append(signal.completion().disposition()).append('\n');
    if (signal.completion().outcome() != null) {
      sb.append("tech=").append(signal.completion().outcome().technicalStatus()).append('\n');
      if (signal.completion().outcome().canonicalData() != null) {
        sb.append("data=").append(signal.completion().outcome().canonicalData()).append('\n');
      }
    }
    return sha256(sb.toString());
  }

  @Override
  public String deduplicationKeyHash(String sourceRef, String messageId) {
    return sha256("dedup|" + sourceRef + "|" + messageId);
  }

  private static String sha256(String input) {
    try {
      MessageDigest md = MessageDigest.getInstance("SHA-256");
      byte[] dig = md.digest(input.getBytes(StandardCharsets.UTF_8));
      return HexFormat.of().formatHex(dig);
    } catch (Exception e) {
      throw new IllegalStateException("SHA-256 unavailable", e);
    }
  }
}
