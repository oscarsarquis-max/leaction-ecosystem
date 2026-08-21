package br.com.banco.spider.canonical.contract;

import java.util.Objects;

public record OriginDescriptor(String channel, String originatorId, String interactionRef) {

  public OriginDescriptor {
    Objects.requireNonNull(channel, "channel");
    Objects.requireNonNull(originatorId, "originatorId");
    channel = channel.trim();
    originatorId = originatorId.trim();
    if (channel.isEmpty() || originatorId.isEmpty()) {
      throw new IllegalArgumentException("channel and originatorId must not be blank");
    }
    if (interactionRef != null) {
      interactionRef = interactionRef.trim();
      if (interactionRef.isEmpty()) {
        interactionRef = null;
      }
    }
  }
}
