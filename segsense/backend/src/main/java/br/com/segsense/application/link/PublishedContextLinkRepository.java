package br.com.segsense.application.link;

import br.com.segsense.domain.link.ContextLinkEvent;
import br.com.segsense.domain.link.PublishedContextLink;
import java.util.List;
import java.util.Optional;
import java.util.UUID;

public interface PublishedContextLinkRepository {

  PublishedContextLink saveNew(PublishedContextLink link, ContextLinkEvent issued);

  PublishedContextLink saveRevocation(PublishedContextLink link, ContextLinkEvent revoked);

  Optional<PublishedContextLink> findByScope(
      UUID publisherId, UUID channelId, UUID environmentId, UUID opportunityId, UUID linkId);

  Optional<PublishedContextLink> findByTokenDigest(byte[] digest);

  List<PublishedContextLink> listAfter(
      UUID opportunityId, InstantCursor cursor, boolean hasCursor, int limit);

  List<ContextLinkEvent> listEventsAfter(
      UUID linkId, InstantCursor cursor, boolean hasCursor, int limit);

  record InstantCursor(java.time.Instant occurredAt, UUID id) {}
}
