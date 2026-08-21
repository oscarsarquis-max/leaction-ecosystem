package br.com.banco.spider.operational.readmodel;

public record OperationalSection<T>(boolean available, boolean redacted, String reasonCode, T data) {
  public static <T> OperationalSection<T> of(T data) {
    return new OperationalSection<>(true, false, null, data);
  }

  public static <T> OperationalSection<T> unavailable(String reason) {
    return new OperationalSection<>(false, false, reason, null);
  }

  public static <T> OperationalSection<T> redacted(String reason) {
    return new OperationalSection<>(true, true, reason, null);
  }
}
