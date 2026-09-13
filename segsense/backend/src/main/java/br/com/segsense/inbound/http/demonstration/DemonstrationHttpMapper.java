package br.com.segsense.inbound.http.demonstration;

import br.com.segsense.application.demonstration.GetPublishedDemonstrationUseCase.PublishedDemonstration;
import br.com.segsense.application.demonstration.ManageDemonstrationStoryUseCase.BlockCommand;
import br.com.segsense.application.demonstration.ManageDemonstrationStoryUseCase.ClaimCommand;
import br.com.segsense.application.demonstration.ManageDemonstrationStoryUseCase.DemonstrationDraftCommand;
import br.com.segsense.domain.demonstration.DemonstrationSource;
import br.com.segsense.domain.demonstration.DemonstrationStory;
import java.util.List;

final class DemonstrationHttpMapper {

  private DemonstrationHttpMapper() {}

  static DemonstrationDraftCommand draft(DemonstrationDraftRequest request) {
    List<BlockCommand> blocks =
        request.blocks() == null
            ? List.of()
            : request.blocks().stream()
                .map(block -> new BlockCommand(block.title(), block.body()))
                .toList();
    List<ClaimCommand> claims =
        request.claims() == null
            ? List.of()
            : request.claims().stream()
                .map(claim -> new ClaimCommand(claim.text(), claim.sourceKey()))
                .toList();
    return new DemonstrationDraftCommand(
        request.title(),
        request.summary(),
        request.intendedAudience(),
        request.scopeNote(),
        blocks,
        claims);
  }

  static DemonstrationDraftCommand draft(CreateDemonstrationRequest request) {
    List<BlockCommand> blocks =
        request.blocks() == null
            ? List.of()
            : request.blocks().stream()
                .map(block -> new BlockCommand(block.title(), block.body()))
                .toList();
    List<ClaimCommand> claims =
        request.claims() == null
            ? List.of()
            : request.claims().stream()
                .map(claim -> new ClaimCommand(claim.text(), claim.sourceKey()))
                .toList();
    return new DemonstrationDraftCommand(
        request.title(),
        request.summary(),
        request.intendedAudience(),
        request.scopeNote(),
        blocks,
        claims);
  }

  static long expectedVersion(Long version) {
    return version == null ? -1L : version;
  }

  static DemonstrationAdminResponse story(DemonstrationStory story, boolean preview) {
    var revision = story.current();
    return new DemonstrationAdminResponse(
        story.id(),
        story.key().value(),
        story.workflowStatus().name(),
        story.publicationStatus().name(),
        story.currentRevision(),
        story.publishedRevision(),
        story.version(),
        revision.title(),
        revision.summary(),
        revision.intendedAudience(),
        revision.scopeNote(),
        revision.frozen(),
        revision.blocks().stream()
            .map(block -> new DemonstrationAdminResponse.Block(block.position(), block.title(), block.body()))
            .toList(),
        revision.claims().stream()
            .map(
                claim ->
                    new DemonstrationAdminResponse.Claim(
                        claim.position(), claim.text(), claim.sourceId()))
            .toList(),
        preview);
  }

  static DemonstrationSourceResponse source(DemonstrationSource source) {
    return new DemonstrationSourceResponse(
        source.id(),
        source.key(),
        source.url(),
        source.consultedOn().toString(),
        source.accessKind(),
        source.verificationStatus(),
        source.summary());
  }

  static PublicDemonstrationResponse published(PublishedDemonstration published) {
    return new PublicDemonstrationResponse(
        published.key(),
        published.title(),
        published.summary(),
        published.intendedAudience(),
        published.scopeNote(),
        published.revisionNumber(),
        published.publishedAt(),
        published.blocks().stream()
            .map(block -> new PublicDemonstrationResponse.Block(block.position(), block.title(), block.body()))
            .toList(),
        published.references().stream()
            .map(
                reference ->
                    new PublicDemonstrationResponse.Reference(
                        reference.url(), reference.consultedOn(), reference.verificationStatus()))
            .toList());
  }
}
