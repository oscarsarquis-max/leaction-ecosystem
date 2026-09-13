package br.com.segsense.inbound.http.catalog;

import br.com.segsense.application.catalog.CatalogPage;
import br.com.segsense.application.catalog.CatalogPageQuery;
import br.com.segsense.domain.catalog.CanonicalUrl;
import br.com.segsense.domain.catalog.CatalogValidationException;
import br.com.segsense.domain.catalog.Channel;
import br.com.segsense.domain.catalog.ChannelType;
import br.com.segsense.domain.catalog.ContextualEnvironment;
import br.com.segsense.domain.catalog.EnvironmentType;
import br.com.segsense.domain.catalog.LifecycleStatus;
import br.com.segsense.domain.catalog.Publisher;
import java.util.List;
import java.util.Locale;

final class CatalogHttpMapper {

  private CatalogHttpMapper() {}

  static CatalogPageQuery pageQuery(Integer size, String after) {
    return CatalogPageQuery.of(size, after);
  }

  static long expectedVersion(Long version) {
    if (version == null || version < 0) {
      throw new CatalogValidationException("A versão esperada é obrigatória.");
    }
    return version;
  }

  static LifecycleStatus status(String raw) {
    if (raw == null || raw.isBlank()) {
      throw new CatalogValidationException("O status é obrigatório.");
    }
    try {
      return LifecycleStatus.valueOf(raw.trim().toUpperCase(Locale.ROOT));
    } catch (IllegalArgumentException ex) {
      throw new CatalogValidationException("O status informado é inválido.");
    }
  }

  static ChannelType channelType(String raw) {
    if (raw == null || raw.isBlank()) {
      throw new CatalogValidationException("O tipo do canal é obrigatório.");
    }
    try {
      return ChannelType.valueOf(raw.trim().toUpperCase(Locale.ROOT));
    } catch (IllegalArgumentException ex) {
      throw new CatalogValidationException("O tipo do canal é inválido.");
    }
  }

  static EnvironmentType environmentType(String raw) {
    if (raw == null || raw.isBlank()) {
      throw new CatalogValidationException("O tipo do ambiente é obrigatório.");
    }
    try {
      return EnvironmentType.valueOf(raw.trim().toUpperCase(Locale.ROOT));
    } catch (IllegalArgumentException ex) {
      throw new CatalogValidationException("O tipo do ambiente é inválido.");
    }
  }

  static PublisherResponse publisher(Publisher publisher) {
    return new PublisherResponse(
        publisher.id(),
        publisher.key().value(),
        publisher.name().value(),
        publisher.status().name(),
        publisher.version(),
        publisher.createdAt(),
        publisher.updatedAt(),
        publisher.createdBy(),
        publisher.updatedBy(),
        publisher.effectivelyAvailable());
  }

  static ChannelResponse channel(Channel channel, Publisher publisher) {
    return new ChannelResponse(
        channel.id(),
        channel.publisherId(),
        channel.key().value(),
        channel.name().value(),
        channel.type().name(),
        channel.status().name(),
        channel.version(),
        channel.createdAt(),
        channel.updatedAt(),
        channel.createdBy(),
        channel.updatedBy(),
        channel.effectivelyAvailable(publisher));
  }

  static EnvironmentResponse environment(
      ContextualEnvironment environment, Publisher publisher, Channel channel) {
    return new EnvironmentResponse(
        environment.id(),
        environment.publisherId(),
        environment.channelId(),
        environment.key().value(),
        environment.name().value(),
        environment.type().name(),
        environment.canonicalUrl().map(CanonicalUrl::value).orElse(null),
        environment.status().name(),
        environment.version(),
        environment.createdAt(),
        environment.updatedAt(),
        environment.createdBy(),
        environment.updatedBy(),
        environment.effectivelyAvailable(publisher, channel));
  }

  static <T, R> CatalogCollectionResponse<R> collection(
      CatalogPage<T> page, java.util.function.Function<T, R> mapper) {
    List<R> items = page.items().stream().map(mapper).toList();
    return new CatalogCollectionResponse<>(
        items, new CatalogPageResponse(page.size(), page.next()));
  }
}
