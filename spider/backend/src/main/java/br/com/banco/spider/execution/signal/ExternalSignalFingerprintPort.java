package br.com.banco.spider.execution.signal;

public interface ExternalSignalFingerprintPort {
  String fingerprint(ExternalSignalEnvelope signal);

  String fingerprintVersion();
}
