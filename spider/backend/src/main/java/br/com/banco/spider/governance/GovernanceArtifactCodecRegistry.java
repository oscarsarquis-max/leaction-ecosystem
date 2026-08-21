package br.com.banco.spider.governance;

import com.fasterxml.jackson.annotation.JsonAutoDetect;
import com.fasterxml.jackson.annotation.PropertyAccessor;
import com.fasterxml.jackson.databind.DeserializationFeature;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.SerializationFeature;
import com.fasterxml.jackson.datatype.jsr310.JavaTimeModule;
import java.util.Objects;
import org.springframework.stereotype.Component;

/**
 * Codecs fechados — sem polymorphic typing. Conteúdo é JSON tipado por artifactType conhecido.
 */
@Component
public class GovernanceArtifactCodecRegistry {

  private final ObjectMapper mapper;

  public GovernanceArtifactCodecRegistry() {
    this.mapper =
        new ObjectMapper()
            .registerModule(new JavaTimeModule())
            .setVisibility(PropertyAccessor.ALL, JsonAutoDetect.Visibility.NONE)
            .setVisibility(PropertyAccessor.FIELD, JsonAutoDetect.Visibility.ANY)
            .configure(DeserializationFeature.FAIL_ON_UNKNOWN_PROPERTIES, true)
            .configure(DeserializationFeature.FAIL_ON_MISSING_CREATOR_PROPERTIES, false)
            .configure(SerializationFeature.ORDER_MAP_ENTRIES_BY_KEYS, true)
            .disable(SerializationFeature.WRITE_DATES_AS_TIMESTAMPS);
  }

  public String canonicalize(GovernanceArtifactType type, Object domainObject) {
    Objects.requireNonNull(type, "type");
    Objects.requireNonNull(domainObject, "domainObject");
    try {
      validateTypeMatch(type, domainObject);
      return mapper.writeValueAsString(domainObject);
    } catch (IllegalArgumentException ex) {
      throw ex;
    } catch (Exception ex) {
      throw new IllegalArgumentException("CODEC_ENCODE_FAILED");
    }
  }

  public <T> T decode(GovernanceArtifactType type, String canonicalContent, Class<T> clazz) {
    Objects.requireNonNull(type, "type");
    Objects.requireNonNull(canonicalContent, "canonicalContent");
    if (canonicalContent.length() > 262_144) {
      throw new IllegalArgumentException("ARTIFACT_TOO_LARGE");
    }
    try {
      T value = mapper.readValue(canonicalContent, clazz);
      validateTypeMatch(type, value);
      return value;
    } catch (IllegalArgumentException ex) {
      throw ex;
    } catch (Exception ex) {
      throw new IllegalArgumentException("CODEC_DECODE_FAILED:" + ex.getMessage(), ex);
    }
  }

  private static void validateTypeMatch(GovernanceArtifactType type, Object value) {
    boolean ok =
        switch (type) {
          case ROUTE_DEFINITION -> value instanceof br.com.banco.spider.execution.route.RouteDefinition;
          case RETRY_POLICY -> value instanceof br.com.banco.spider.execution.retry.RetryPolicyDefinition;
          case WAIT_POLICY -> value instanceof br.com.banco.spider.execution.wait.WaitPolicyDefinition;
          case CALLBACK_DEFINITION ->
              value instanceof br.com.banco.spider.execution.callback.CallbackDefinition;
          case CALLBACK_DELIVERY_POLICY ->
              value instanceof br.com.banco.spider.execution.callback.CallbackDeliveryPolicy;
          case CALLBACK_RECONCILIATION_POLICY ->
              value instanceof br.com.banco.spider.execution.callback.CallbackReconciliationPolicy;
          case INTEGRITY_PROFILE ->
              value instanceof br.com.banco.spider.security.integrity.IntegrityProfileDefinition;
          case ADAPTER_BINDING_DESCRIPTOR,
                  CALLBACK_BINDING_DESCRIPTOR,
                  STATUS_QUERY_BINDING_DESCRIPTOR ->
              value instanceof BindingDescriptor;
          case EXTERNAL_SIGNAL_DEFINITION ->
              value instanceof br.com.banco.spider.execution.signal.ExternalSignalDefinition;
          case DATA_PROTECTION_PROFILE ->
              value
                  instanceof
                  br.com.banco.spider.security.dataprotection.DataProtectionProfileDefinition;
        };
    if (!ok) {
      throw new IllegalArgumentException("CODEC_TYPE_MISMATCH");
    }
  }

  public Class<?> domainClass(GovernanceArtifactType type) {
    return switch (type) {
      case ROUTE_DEFINITION -> br.com.banco.spider.execution.route.RouteDefinition.class;
      case RETRY_POLICY -> br.com.banco.spider.execution.retry.RetryPolicyDefinition.class;
      case WAIT_POLICY -> br.com.banco.spider.execution.wait.WaitPolicyDefinition.class;
      case CALLBACK_DEFINITION -> br.com.banco.spider.execution.callback.CallbackDefinition.class;
      case CALLBACK_DELIVERY_POLICY ->
          br.com.banco.spider.execution.callback.CallbackDeliveryPolicy.class;
      case CALLBACK_RECONCILIATION_POLICY ->
          br.com.banco.spider.execution.callback.CallbackReconciliationPolicy.class;
      case INTEGRITY_PROFILE ->
          br.com.banco.spider.security.integrity.IntegrityProfileDefinition.class;
      case ADAPTER_BINDING_DESCRIPTOR,
          CALLBACK_BINDING_DESCRIPTOR,
          STATUS_QUERY_BINDING_DESCRIPTOR -> BindingDescriptor.class;
      case EXTERNAL_SIGNAL_DEFINITION ->
          br.com.banco.spider.execution.signal.ExternalSignalDefinition.class;
      case DATA_PROTECTION_PROFILE ->
          br.com.banco.spider.security.dataprotection.DataProtectionProfileDefinition.class;
    };
  }
}
