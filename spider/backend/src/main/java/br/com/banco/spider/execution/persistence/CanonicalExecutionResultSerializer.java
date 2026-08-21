package br.com.banco.spider.execution.persistence;

import br.com.banco.spider.canonical.contract.CanonicalExecutionResult;
import br.com.banco.spider.execution.support.IntegrityDigestPort;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.SerializationFeature;
import java.nio.charset.StandardCharsets;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

/** Serializa resultado canônico para persistência técnica (sem logar conteúdo). */
@Component
public class CanonicalExecutionResultSerializer {

  private final ObjectMapper mapper;
  private final IntegrityDigestPort digest;
  private final int maxBytes;

  public CanonicalExecutionResultSerializer(
      ObjectMapper objectMapper,
      IntegrityDigestPort digest,
      @Value("${spider.canonical.persistence.result.max-bytes:65536}") int maxBytes) {
    this.mapper =
        objectMapper.copy().configure(SerializationFeature.ORDER_MAP_ENTRIES_BY_KEYS, true);
    this.digest = digest;
    this.maxBytes = maxBytes;
  }

  public SerializedResult serialize(CanonicalExecutionResult result) {
    try {
      String json = mapper.writeValueAsString(result);
      byte[] bytes = json.getBytes(StandardCharsets.UTF_8);
      if (bytes.length > maxBytes) {
        throw new ResultSizeExceededException(
            "Persisted result exceeds max-bytes=" + maxBytes + " size=" + bytes.length);
      }
      return new SerializedResult(json, digest.digest(json));
    } catch (ResultSizeExceededException e) {
      throw e;
    } catch (Exception e) {
      throw new IllegalStateException("Failed to serialize execution result", e);
    }
  }

  public CanonicalExecutionResult deserialize(String representation, String expectedDigest) {
    String actual = digest.digest(representation);
    if (!actual.equals(expectedDigest)) {
      throw new ResultDigestMismatchException("Persisted result digest mismatch");
    }
    try {
      return mapper.readValue(representation, CanonicalExecutionResult.class);
    } catch (Exception e) {
      throw new IllegalStateException("Failed to deserialize execution result", e);
    }
  }

  public record SerializedResult(String representation, String contentDigest) {}

  public static final class ResultSizeExceededException extends RuntimeException {
    public ResultSizeExceededException(String message) {
      super(message);
    }
  }

  public static final class ResultDigestMismatchException extends RuntimeException {
    public ResultDigestMismatchException(String message) {
      super(message);
    }
  }
}
