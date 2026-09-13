package br.com.segsense.domain.identity;

/**
 * Channel known through a legitimate server-side source. A channel identifier does not grant
 * authorization by itself.
 */
public record ChannelContext(String channelId) {

  public ChannelContext {
    channelId = IdentityValues.requireNormalized(channelId, "channelId");
  }

  public static ChannelContext of(String channelId) {
    return new ChannelContext(channelId);
  }
}
