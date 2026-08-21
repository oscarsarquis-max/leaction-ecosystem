package br.com.banco.spider.governance.port;

/** Informa se snapshot ainda é referenciado por work items / fixations. */
public interface GovernanceSnapshotReferenceStorePort {
  boolean isReferencedByActiveWork(String snapshotId);

  long countFixations(String snapshotId);
}
