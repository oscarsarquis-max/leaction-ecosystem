package br.com.banco.spider.execution.signal;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import br.com.banco.spider.governance.GovernanceArtifactCodecRegistry;
import br.com.banco.spider.governance.GovernanceArtifactType;
import br.com.banco.spider.governance.GovernanceLifecycleState;
import java.time.Duration;
import java.util.List;
import org.junit.jupiter.api.Test;

class ExternalSignalDefinitionCodecTest {

  @Test
  void codecRoundTripAndEligibility() {
    GovernanceArtifactCodecRegistry codecs = new GovernanceArtifactCodecRegistry();
    ExternalSignalDefinition def =
        ExternalSignalDefinition.publishedMock(
            "async-completion",
            "1.0.0",
            "contract:signal:async-completion@1.0",
            "profile:signal:test@1.0");
    String json =
        codecs.canonicalize(GovernanceArtifactType.EXTERNAL_SIGNAL_DEFINITION, def);
    ExternalSignalDefinition decoded =
        codecs.decode(
            GovernanceArtifactType.EXTERNAL_SIGNAL_DEFINITION,
            json,
            ExternalSignalDefinition.class);
    assertEquals(def.ref(), decoded.ref());
    assertTrue(decoded.isEligible());
    assertEquals(GovernanceLifecycleState.PUBLISHED, decoded.status());
    assertEquals(LateSignalPolicy.RECORD_ONLY, decoded.lateSignalPolicy());
    assertEquals(Duration.ofHours(24), decoded.replayWindow());
    assertEquals(List.of("ASYNC_COMPLETION", "STATUS_UPDATE"), decoded.allowedEventTypes());
  }
}
