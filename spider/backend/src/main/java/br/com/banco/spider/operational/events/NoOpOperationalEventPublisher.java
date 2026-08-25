package br.com.banco.spider.operational.events;

public final class NoOpOperationalEventPublisher implements OperationalEventPublisher {

  static final NoOpOperationalEventPublisher INSTANCE = new NoOpOperationalEventPublisher();

  public NoOpOperationalEventPublisher() {}

  @Override
  public void publish(OperationalEventDraft draft) {
    // Telemetry is disabled.
  }
}
