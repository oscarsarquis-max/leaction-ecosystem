package br.com.segsense.application.consent;

import br.com.segsense.domain.consent.ConsentNotice;
import java.util.Optional;
import java.util.UUID;

public interface ConsentNoticeRepository {

  ConsentNotice saveNew(ConsentNotice notice);

  ConsentNotice saveSnapshot(ConsentNotice notice);

  ConsentNotice saveStatus(ConsentNotice notice);

  Optional<ConsentNotice> findByScope(
      UUID publisherId, UUID channelId, UUID environmentId, UUID opportunityId);

  Optional<ConsentNotice> findApprovedByOpportunityRevisionId(UUID opportunityRevisionId);
}
