package br.com.banco.spider.governance.port;

/** Registry leve de snapshots revogados — sem recompilar snapshot. */
public interface GovernanceRevocationRegistryPort {
  boolean isSnapshotRevoked(String snapshotId);

  void markRevoked(String snapshotId, String reasonCode);
}
