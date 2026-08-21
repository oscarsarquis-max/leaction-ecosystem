package br.com.banco.spider.security.dataprotection;

import java.nio.charset.StandardCharsets;
import java.security.SecureRandom;
import java.util.Arrays;
import java.util.Base64;
import java.util.Objects;
import javax.crypto.Cipher;
import javax.crypto.SecretKey;
import javax.crypto.spec.GCMParameterSpec;
import javax.crypto.spec.SecretKeySpec;
import org.springframework.beans.factory.ObjectProvider;
import org.springframework.stereotype.Service;
import reactor.core.publisher.Mono;

@Service
public class ProtectedPayloadService {

  public static final String DOMAIN = "SPIDER_SIGNAL_ENVELOPE_AT_REST_V1";
  private static final int IV_BYTES = 12;
  private static final int TAG_BITS = 128;

  private final ObjectProvider<DataProtectionKeyMaterialProviderPort> keyProvider;
  private final SecureRandom secureRandom;

  @org.springframework.beans.factory.annotation.Autowired
  public ProtectedPayloadService(
      ObjectProvider<DataProtectionKeyMaterialProviderPort> keyProvider,
      ObjectProvider<SecureRandom> secureRandom) {
    this.keyProvider = keyProvider;
    SecureRandom injected = secureRandom == null ? null : secureRandom.getIfAvailable();
    this.secureRandom = injected != null ? injected : new SecureRandom();
  }

  /** Test / explicit wiring. */
  public static ProtectedPayloadService forTests(
      DataProtectionKeyMaterialProviderPort provider, SecureRandom secureRandom) {
    return new ProtectedPayloadService(
        new ObjectProvider<>() {
          @Override
          public DataProtectionKeyMaterialProviderPort getObject() {
            return provider;
          }

          @Override
          public DataProtectionKeyMaterialProviderPort getObject(Object... args) {
            return provider;
          }

          @Override
          public DataProtectionKeyMaterialProviderPort getIfAvailable() {
            return provider;
          }

          @Override
          public DataProtectionKeyMaterialProviderPort getIfUnique() {
            return provider;
          }
        },
        new ObjectProvider<>() {
          @Override
          public SecureRandom getObject() {
            return secureRandom;
          }

          @Override
          public SecureRandom getObject(Object... args) {
            return secureRandom;
          }

          @Override
          public SecureRandom getIfAvailable() {
            return secureRandom;
          }

          @Override
          public SecureRandom getIfUnique() {
            return secureRandom;
          }
        });
  }

  public record ProtectedPayload(
      String algorithm,
      String keyRef,
      String keyVersion,
      String aadVersion,
      byte[] iv,
      byte[] ciphertextAndTag,
      int plaintextSize) {}

  public record DataProtectionContext(
      DataProtectionProfileDefinition profile,
      String inboxId,
      String executionId,
      String waitId,
      String signalDefinitionRef,
      String payloadSchemaVersion,
      java.time.Instant createdAt) {}

  public Mono<ProtectedPayload> protect(byte[] plaintext, DataProtectionContext context) {
    Objects.requireNonNull(plaintext, "plaintext");
    Objects.requireNonNull(context, "context");
    DataProtectionKeyMaterialProviderPort provider = keyProvider.getIfAvailable();
    if (provider == null) {
      return Mono.error(new IllegalStateException("KEY_PROVIDER_UNAVAILABLE"));
    }
    if (plaintext.length > context.profile().maximumPlaintextBytes()) {
      return Mono.error(new IllegalArgumentException("PLAINTEXT_TOO_LARGE"));
    }
    DataProtectionKeyReference ref =
        new DataProtectionKeyReference(
            context.profile().keyRef(),
            context.profile().activeKeyVersion(),
            context.profile().purpose(),
            context.profile().algorithm());
    return provider
        .resolveForEncryption(ref)
        .map(
            handle -> {
              try (handle) {
                return encrypt(plaintext, context, handle);
              } catch (Exception ex) {
                throw new IllegalStateException("ENCRYPT_FAILED");
              }
            });
  }

  public Mono<byte[]> unprotect(ProtectedPayload protectedPayload, DataProtectionContext context) {
    Objects.requireNonNull(protectedPayload, "protectedPayload");
    DataProtectionKeyMaterialProviderPort provider = keyProvider.getIfAvailable();
    if (provider == null) {
      return Mono.error(new IllegalStateException("KEY_PROVIDER_UNAVAILABLE"));
    }
    if (!context.profile().canDecryptWith(protectedPayload.keyVersion())) {
      return Mono.error(new IllegalStateException("KEY_VERSION_NOT_ACCEPTED"));
    }
    DataProtectionKeyReference ref =
        new DataProtectionKeyReference(
            protectedPayload.keyRef(),
            protectedPayload.keyVersion(),
            context.profile().purpose(),
            context.profile().algorithm());
    return provider
        .resolveForDecryption(ref)
        .map(
            handle -> {
              try (handle) {
                return decrypt(protectedPayload, context, handle);
              } catch (Exception ex) {
                throw new IllegalStateException("DECRYPT_FAILED");
              }
            });
  }

  private ProtectedPayload encrypt(
      byte[] plaintext, DataProtectionContext context, DataProtectionKeyHandle handle)
      throws Exception {
    byte[] iv = new byte[IV_BYTES];
    secureRandom.nextBytes(iv);
    byte[] aad = buildAad(context, handle.keyRef(), handle.keyVersion());
    byte[] key = handle.keyMaterialCopy();
    try {
      Cipher cipher = Cipher.getInstance("AES/GCM/NoPadding");
      SecretKey sk = new SecretKeySpec(key, "AES");
      cipher.init(Cipher.ENCRYPT_MODE, sk, new GCMParameterSpec(TAG_BITS, iv));
      cipher.updateAAD(aad);
      byte[] ct = cipher.doFinal(plaintext);
      return new ProtectedPayload(
          DataProtectionAlgorithm.AES_256_GCM.name(),
          handle.keyRef(),
          handle.keyVersion(),
          "V1",
          iv,
          ct,
          plaintext.length);
    } finally {
      Arrays.fill(key, (byte) 0);
    }
  }

  private byte[] decrypt(
      ProtectedPayload payload, DataProtectionContext context, DataProtectionKeyHandle handle)
      throws Exception {
    byte[] aad = buildAad(context, payload.keyRef(), payload.keyVersion());
    byte[] key = handle.keyMaterialCopy();
    try {
      Cipher cipher = Cipher.getInstance("AES/GCM/NoPadding");
      SecretKey sk = new SecretKeySpec(key, "AES");
      cipher.init(Cipher.DECRYPT_MODE, sk, new GCMParameterSpec(TAG_BITS, payload.iv()));
      cipher.updateAAD(aad);
      return cipher.doFinal(payload.ciphertextAndTag());
    } finally {
      Arrays.fill(key, (byte) 0);
    }
  }

  static byte[] buildAad(DataProtectionContext ctx, String keyRef, String keyVersion) {
    String canonical =
        DOMAIN
            + "|"
            + nullSafe(ctx.inboxId())
            + "|"
            + nullSafe(ctx.executionId())
            + "|"
            + nullSafe(ctx.waitId())
            + "|"
            + nullSafe(ctx.signalDefinitionRef())
            + "|"
            + ctx.profile().exactRef()
            + "|"
            + keyRef
            + "|"
            + keyVersion
            + "|"
            + nullSafe(ctx.payloadSchemaVersion())
            + "|"
            + (ctx.createdAt() == null ? "" : ctx.createdAt().toString());
    return canonical.getBytes(StandardCharsets.UTF_8);
  }

  private static String nullSafe(String v) {
    return v == null ? "" : v;
  }

  public static String encodeB64(byte[] bytes) {
    return Base64.getEncoder().encodeToString(bytes);
  }

  public static byte[] decodeB64(String s) {
    return Base64.getDecoder().decode(s);
  }
}
