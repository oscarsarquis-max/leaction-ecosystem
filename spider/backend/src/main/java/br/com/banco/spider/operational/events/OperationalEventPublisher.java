package br.com.banco.spider.operational.events;

public interface OperationalEventPublisher {
  void publish(OperationalEventDraft draft);

  static OperationalEventPublisher noop() {
    return NoOpOperationalEventPublisher.INSTANCE;
  }
}
