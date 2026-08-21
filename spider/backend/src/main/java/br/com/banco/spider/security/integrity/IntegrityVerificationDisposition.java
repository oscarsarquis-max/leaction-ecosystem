package br.com.banco.spider.security.integrity;

public enum IntegrityVerificationDisposition {
  VERIFIED,
  INVALID_MAC,
  EXPIRED,
  ISSUED_IN_FUTURE,
  NONCE_MISSING,
  PROFILE_NOT_ALLOWED,
  KEY_VERSION_NOT_ALLOWED,
  KEY_UNAVAILABLE,
  MALFORMED_PROOF,
  PAYLOAD_DIGEST_MISMATCH
}
