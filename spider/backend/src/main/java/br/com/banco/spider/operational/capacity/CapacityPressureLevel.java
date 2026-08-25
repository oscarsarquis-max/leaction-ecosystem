package br.com.banco.spider.operational.capacity;

/** Nível de pressão observado em um escopo. {@code UNKNOWN} nunca é lido como saudável. */
public enum CapacityPressureLevel {
  NORMAL,
  ELEVATED,
  HIGH,
  CRITICAL,
  UNKNOWN
}
