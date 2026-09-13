package br.com.segsense.application.consent;

import br.com.segsense.application.catalog.CatalogActor;
import br.com.segsense.application.opportunity.OpportunityCommandSupport;
import br.com.segsense.domain.catalog.ResourceNotFoundException;
import br.com.segsense.domain.consent.ConsentNotice;
import br.com.segsense.domain.consent.ConsentNoticeContent;
import br.com.segsense.domain.opportunity.AdministrativeJustification;
import java.time.Clock;
import java.util.UUID;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class ManageConsentNoticeUseCase {

  private final ConsentNoticeRepository notices;
  private final OpportunityCommandSupport support;
  private final Clock clock;

  public ManageConsentNoticeUseCase(
      ConsentNoticeRepository notices, OpportunityCommandSupport support, Clock clock) {
    this.notices = notices;
    this.support = support;
    this.clock = clock;
  }

  @Transactional(readOnly = true)
  public ConsentNotice get(
      UUID publisherId, UUID channelId, UUID environmentId, UUID opportunityId) {
    support.load(publisherId, channelId, environmentId, opportunityId);
    return notices
        .findByScope(publisherId, channelId, environmentId, opportunityId)
        .orElseThrow(ResourceNotFoundException::new);
  }

  @Transactional
  public ConsentNotice create(
      CatalogActor actor,
      UUID publisherId,
      UUID channelId,
      UUID environmentId,
      UUID opportunityId,
      ConsentNoticeContent content) {
    var loaded = support.load(publisherId, channelId, environmentId, opportunityId);
    ConsentNotice notice =
        ConsentNotice.create(
            UUID.randomUUID(),
            loaded.opportunity(),
            content,
            clock.instant(),
            support.requireActor(actor).subjectId());
    return notices.saveNew(notice);
  }

  @Transactional
  public ConsentNotice editDraft(
      CatalogActor actor,
      UUID publisherId,
      UUID channelId,
      UUID environmentId,
      UUID opportunityId,
      long expectedVersion,
      ConsentNoticeContent content) {
    var loaded = support.load(publisherId, channelId, environmentId, opportunityId);
    ConsentNotice notice = get(publisherId, channelId, environmentId, opportunityId);
    notice.editDraft(
        content, loaded.opportunity(), expectedVersion, clock.instant(), actor.subjectId());
    return notices.saveSnapshot(notice);
  }

  @Transactional
  public ConsentNotice approve(
      CatalogActor actor,
      UUID publisherId,
      UUID channelId,
      UUID environmentId,
      UUID opportunityId,
      long expectedVersion,
      String justification) {
    support.load(publisherId, channelId, environmentId, opportunityId);
    ConsentNotice notice = get(publisherId, channelId, environmentId, opportunityId);
    notice.approve(
        AdministrativeJustification.required(justification),
        expectedVersion,
        clock.instant(),
        support.requireActor(actor).subjectId());
    return notices.saveStatus(notice);
  }

  @Transactional
  public ConsentNotice retire(
      CatalogActor actor,
      UUID publisherId,
      UUID channelId,
      UUID environmentId,
      UUID opportunityId,
      long expectedVersion,
      String justification) {
    support.load(publisherId, channelId, environmentId, opportunityId);
    ConsentNotice notice = get(publisherId, channelId, environmentId, opportunityId);
    notice.retire(
        AdministrativeJustification.required(justification),
        expectedVersion,
        clock.instant(),
        actor.subjectId());
    return notices.saveStatus(notice);
  }
}
