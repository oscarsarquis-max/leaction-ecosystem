package br.com.segsense.application.consent;

import br.com.segsense.application.correlation.CorrelationContext;
import br.com.segsense.application.link.OpaqueTokenGenerator;
import br.com.segsense.application.link.ResolvePublicContextLinkUseCase;
import br.com.segsense.domain.consent.CollectedFieldValue;
import br.com.segsense.domain.consent.ConsentDecision;
import br.com.segsense.domain.consent.ConsentNotice;
import br.com.segsense.domain.consent.ConsentNoticeField;
import br.com.segsense.domain.consent.ContextInstance;
import br.com.segsense.domain.consent.ContextInstanceNotFoundException;
import br.com.segsense.domain.consent.ContinuityUnavailableException;
import br.com.segsense.domain.consent.IdempotencyKey;
import br.com.segsense.domain.consent.InstanceCredentialNotReplayableException;
import br.com.segsense.domain.consent.InvalidCollectedValueException;
import br.com.segsense.domain.link.OpaqueToken;
import br.com.segsense.domain.link.PublishedContextLink;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.time.Clock;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.UUID;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class ManageContextInstanceUseCase {

  public static final String CREDENTIAL_HEADER = "X-SegSense-Instance-Credential";

  private final ResolvePublicContextLinkUseCase resolve;
  private final ConsentNoticeRepository notices;
  private final ContextInstanceRepository instances;
  private final OpaqueTokenGenerator tokens;
  private final ContextInstanceTtlSettings ttl;
  private final Clock clock;

  public ManageContextInstanceUseCase(
      ResolvePublicContextLinkUseCase resolve,
      ConsentNoticeRepository notices,
      ContextInstanceRepository instances,
      OpaqueTokenGenerator tokens,
      ContextInstanceTtlSettings ttl,
      Clock clock) {
    this.resolve = resolve;
    this.notices = notices;
    this.instances = instances;
    this.tokens = tokens;
    this.ttl = ttl;
    this.clock = clock;
  }

  @Transactional
  public CreatedInstance create(String opaqueToken, String idempotencyKey) {
    ResolvePublicContextLinkUseCase.ResolvedPublicContext resolved = resolve.requireActive(opaqueToken);
    ConsentNotice notice =
        notices
            .findApprovedByOpportunityRevisionId(resolved.link().opportunityRevisionId())
            .orElseThrow(ContinuityUnavailableException::new);
    byte[] idempotencyDigest = digestKey(opaqueToken, IdempotencyKey.required(idempotencyKey));
    if (instances.findByIdempotencyKeyDigest(idempotencyDigest).isPresent()) {
      throw new InstanceCredentialNotReplayableException();
    }
    String raw = tokens.generate();
    UUID correlation =
        CorrelationContext.current() == null ? UUID.randomUUID() : CorrelationContext.current();
    ContextInstance instance =
        ContextInstance.create(
            UUID.randomUUID(),
            resolved.link(),
            resolved.opportunity(),
            notice,
            raw,
            idempotencyDigest,
            ttl.ttl(),
            clock.instant(),
            correlation);
    ContextInstance saved = instances.saveNew(instance);
    return new CreatedInstance(saved, raw);
  }

  @Transactional(readOnly = true)
  public ContextInstance current(String opaqueToken, String rawCredential) {
    return requireActiveInstance(opaqueToken, rawCredential);
  }

  @Transactional
  public ContextInstance putValues(
      String opaqueToken, String rawCredential, long expectedVersion, List<CollectedValueDraft> values) {
    ResolvePublicContextLinkUseCase.ResolvedPublicContext resolved = resolve.requireActive(opaqueToken);
    ContextInstance instance = requireMatchingInstance(resolved.link(), rawCredential);
    instance.requireContinuityStillEffective(resolved.notice());
    instance.replaceValues(parseValues(instance, values), expectedVersion, clock.instant());
    return instances.saveValues(instance);
  }

  @Transactional
  public ContextInstance authorize(
      String opaqueToken,
      String rawCredential,
      long expectedVersion,
      int noticeVersion,
      boolean acknowledged) {
    ResolvePublicContextLinkUseCase.ResolvedPublicContext resolved = resolve.requireActive(opaqueToken);
    ContextInstance instance = requireMatchingInstance(resolved.link(), rawCredential);
    instance.requireContinuityStillEffective(resolved.notice());
    UUID correlation =
        CorrelationContext.current() == null ? UUID.randomUUID() : CorrelationContext.current();
    ConsentDecision decision =
        instance.authorize(expectedVersion, noticeVersion, acknowledged, clock.instant(), correlation);
    return instances.saveDecision(instance, decision);
  }

  @Transactional
  public ContextInstance withdraw(String opaqueToken, String rawCredential, long expectedVersion) {
    PublishedContextLink link = resolve.requireExisting(opaqueToken);
    ContextInstance instance = requireMatchingInstance(link, rawCredential);
    UUID correlation =
        CorrelationContext.current() == null ? UUID.randomUUID() : CorrelationContext.current();
    ConsentDecision decision = instance.withdraw(expectedVersion, clock.instant(), correlation);
    return instances.saveDecision(instance, decision);
  }

  private ContextInstance requireActiveInstance(String opaqueToken, String rawCredential) {
    ResolvePublicContextLinkUseCase.ResolvedPublicContext resolved = resolve.requireActive(opaqueToken);
    return requireMatchingInstance(resolved.link(), rawCredential);
  }

  private ContextInstance requireMatchingInstance(PublishedContextLink link, String rawCredential) {
    if (!OpaqueToken.isWellFormed(rawCredential)) {
      throw new ContextInstanceNotFoundException();
    }
    ContextInstance instance =
        instances
            .findByCredentialDigest(OpaqueToken.digest(rawCredential))
            .orElseThrow(ContextInstanceNotFoundException::new);
    if (!instance.linkId().equals(link.id())
        || !ContextInstance.credentialMatches(instance.credentialDigest(), rawCredential)) {
      throw new ContextInstanceNotFoundException();
    }
    return instance;
  }

  private List<CollectedFieldValue> parseValues(
      ContextInstance instance, List<CollectedValueDraft> drafts) {
    if (drafts == null) {
      throw new InvalidCollectedValueException();
    }
    Map<String, ConsentNoticeField> allowed =
        instance.collectibleFields().stream()
            .collect(java.util.stream.Collectors.toMap(ConsentNoticeField::fieldKey, field -> field));
    Set<String> seen = new HashSet<>();
    List<CollectedFieldValue> parsed = new ArrayList<>();
    for (CollectedValueDraft draft : drafts) {
      if (draft == null || draft.key() == null || seen.contains(draft.key())) {
        throw new InvalidCollectedValueException();
      }
      ConsentNoticeField field = allowed.get(draft.key());
      if (field == null) {
        throw new InvalidCollectedValueException();
      }
      if (draft.type() != null && !draft.type().equals(field.fieldType().name())) {
        throw new InvalidCollectedValueException();
      }
      seen.add(draft.key());
      parsed.add(CollectedFieldValue.parse(UUID.randomUUID(), field, draft.value()));
    }
    return parsed;
  }

  private static byte[] digestKey(String opaqueToken, String idempotencyKey) {
    try {
      return MessageDigest.getInstance("SHA-256")
          .digest((opaqueToken + "\n" + idempotencyKey).getBytes(StandardCharsets.UTF_8));
    } catch (NoSuchAlgorithmException exception) {
      throw new IllegalStateException("SHA-256 required", exception);
    }
  }

  public record CollectedValueDraft(String key, String type, Object value) {}

  public record CreatedInstance(ContextInstance instance, String rawCredential) {}
}
