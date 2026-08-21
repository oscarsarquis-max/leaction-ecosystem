package br.com.banco.spider.execution.signal.protection;

import br.com.banco.spider.execution.signal.ExternalSignalEnvelope;
import com.fasterxml.jackson.annotation.JsonAutoDetect;
import com.fasterxml.jackson.annotation.PropertyAccessor;
import com.fasterxml.jackson.databind.DeserializationFeature;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.SerializationFeature;
import com.fasterxml.jackson.datatype.jsr310.JavaTimeModule;
import java.nio.charset.StandardCharsets;
import java.time.Instant;
import java.util.Objects;
import org.springframework.stereotype.Component;

@Component
public class VerifiedSignalEnvelopeCodec {

  public static final String SCHEMA = "VERIFIED_SIGNAL_ENVELOPE_V1";
  private static final int MAX_BYTES = 262_144;

  private final ObjectMapper mapper;

  public VerifiedSignalEnvelopeCodec() {
    this.mapper =
        new ObjectMapper()
            .registerModule(new JavaTimeModule())
            .setVisibility(PropertyAccessor.ALL, JsonAutoDetect.Visibility.NONE)
            .setVisibility(PropertyAccessor.FIELD, JsonAutoDetect.Visibility.ANY)
            .configure(DeserializationFeature.FAIL_ON_UNKNOWN_PROPERTIES, true)
            .configure(SerializationFeature.ORDER_MAP_ENTRIES_BY_KEYS, true)
            .disable(SerializationFeature.WRITE_DATES_AS_TIMESTAMPS);
  }

  public byte[] encode(ExternalSignalEnvelope envelope, Instant verifiedAt) {
    Objects.requireNonNull(envelope, "envelope");
    try {
      CanonicalVerifiedEnvelope v1 =
          new CanonicalVerifiedEnvelope(
              SCHEMA,
              envelope.messageId(),
              envelope.sourceRef(),
              envelope.bindingRef(),
              envelope.contractRef(),
              envelope.executionId(),
              envelope.stepId(),
              envelope.externalOperationRef(),
              envelope.completion().disposition().name(),
              envelope.completion().outcome() == null
                  ? null
                  : mapper.writeValueAsString(envelope.completion().outcome().canonicalData()),
              envelope.receivedAt() == null ? null : envelope.receivedAt().toString(),
              verifiedAt == null ? null : verifiedAt.toString(),
              envelope.correlationId(),
              envelope.securityContext() == null
                  ? null
                  : envelope.securityContext().securityProfileRef());
      byte[] json = mapper.writeValueAsBytes(v1);
      if (json.length > MAX_BYTES) {
        throw new IllegalArgumentException("ENVELOPE_TOO_LARGE");
      }
      return json;
    } catch (IllegalArgumentException ex) {
      throw ex;
    } catch (Exception ex) {
      throw new IllegalArgumentException("ENVELOPE_ENCODE_FAILED");
    }
  }

  public CanonicalVerifiedEnvelope decode(byte[] bytes) {
    Objects.requireNonNull(bytes, "bytes");
    if (bytes.length > MAX_BYTES) {
      throw new IllegalArgumentException("ENVELOPE_TOO_LARGE");
    }
    try {
      CanonicalVerifiedEnvelope v = mapper.readValue(bytes, CanonicalVerifiedEnvelope.class);
      if (!SCHEMA.equals(v.schemaVersion())) {
        throw new IllegalArgumentException("UNKNOWN_ENVELOPE_SCHEMA");
      }
      return v;
    } catch (IllegalArgumentException ex) {
      throw ex;
    } catch (Exception ex) {
      throw new IllegalArgumentException("ENVELOPE_DECODE_FAILED");
    }
  }

  public String utf8Digest(byte[] bytes, br.com.banco.spider.execution.fingerprint.Sha256IdempotencyKeyHash sha) {
    return sha.hash(new String(bytes, StandardCharsets.UTF_8));
  }

  public record CanonicalVerifiedEnvelope(
      String schemaVersion,
      String messageId,
      String sourceRef,
      String bindingRef,
      String contractRef,
      String executionId,
      String stepId,
      String externalOperationRef,
      String disposition,
      String outcomeCanonicalJson,
      String receivedAt,
      String verifiedAt,
      String correlationId,
      String securityProfileRef) {}
}
