package br.com.banco.spider.config;

import br.com.banco.spider.execution.support.SpiderClock;
import br.com.banco.spider.governance.DefaultActiveGovernanceSnapshotProvider;
import br.com.banco.spider.governance.GovernanceApprovalPolicy;
import br.com.banco.spider.governance.GovernanceArtifactDigestService;
import br.com.banco.spider.governance.GovernanceMode;
import br.com.banco.spider.governance.GovernanceScope;
import br.com.banco.spider.governance.port.ActiveGovernanceSnapshotProviderPort;
import br.com.banco.spider.governance.port.GovernanceActivationStorePort;
import br.com.banco.spider.governance.port.GovernanceArtifactStorePort;
import br.com.banco.spider.governance.port.GovernanceAuditStorePort;
import br.com.banco.spider.governance.port.GovernanceBundleStorePort;
import br.com.banco.spider.governance.port.GovernanceSnapshotStorePort;
import br.com.banco.spider.governance.port.GovernanceValidationReportStorePort;
import br.com.banco.spider.governance.port.ExecutionGovernanceFixationStorePort;
import br.com.banco.spider.governance.port.GovernanceRevocationRegistryPort;
import br.com.banco.spider.governance.port.GovernanceSnapshotReferenceStorePort;
import br.com.banco.spider.infrastructure.persistence.memory.InMemoryExecutionGovernanceFixationStore;
import br.com.banco.spider.infrastructure.persistence.memory.InMemoryGovernanceRevocationRegistry;
import br.com.banco.spider.infrastructure.persistence.memory.InMemoryGovernanceSnapshotReferenceStore;
import br.com.banco.spider.infrastructure.persistence.memory.InMemoryGovernanceStores;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.autoconfigure.condition.ConditionalOnMissingBean;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.context.annotation.Primary;

@Configuration
public class GovernanceConfig {

  @Bean
  @ConditionalOnMissingBean(InMemoryGovernanceStores.class)
  InMemoryGovernanceStores inMemoryGovernanceStores() {
    return new InMemoryGovernanceStores();
  }

  @Bean
  @ConditionalOnMissingBean(ExecutionGovernanceFixationStorePort.class)
  ExecutionGovernanceFixationStorePort executionGovernanceFixationStorePort() {
    return new InMemoryExecutionGovernanceFixationStore();
  }

  @Bean
  @ConditionalOnMissingBean(GovernanceRevocationRegistryPort.class)
  GovernanceRevocationRegistryPort governanceRevocationRegistryPort() {
    return new InMemoryGovernanceRevocationRegistry();
  }

  @Bean
  @ConditionalOnMissingBean(GovernanceSnapshotReferenceStorePort.class)
  GovernanceSnapshotReferenceStorePort governanceSnapshotReferenceStorePort(
      ExecutionGovernanceFixationStorePort fixationStore) {
    return new InMemoryGovernanceSnapshotReferenceStore(fixationStore, null, null, null);
  }

  @Bean
  @ConditionalOnMissingBean(GovernanceArtifactStorePort.class)
  GovernanceArtifactStorePort governanceArtifactStorePort(InMemoryGovernanceStores stores) {
    return stores;
  }

  @Bean
  @ConditionalOnMissingBean(GovernanceBundleStorePort.class)
  GovernanceBundleStorePort governanceBundleStorePort(InMemoryGovernanceStores stores) {
    return stores;
  }

  @Bean
  @ConditionalOnMissingBean(GovernanceValidationReportStorePort.class)
  GovernanceValidationReportStorePort governanceValidationReportStorePort(
      InMemoryGovernanceStores stores) {
    return stores;
  }

  @Bean
  @ConditionalOnMissingBean(GovernanceSnapshotStorePort.class)
  GovernanceSnapshotStorePort governanceSnapshotStorePort(InMemoryGovernanceStores stores) {
    return stores;
  }

  @Bean
  @ConditionalOnMissingBean(GovernanceActivationStorePort.class)
  GovernanceActivationStorePort governanceActivationStorePort(InMemoryGovernanceStores stores) {
    return stores;
  }

  @Bean
  @ConditionalOnMissingBean(GovernanceAuditStorePort.class)
  GovernanceAuditStorePort governanceAuditStorePort(InMemoryGovernanceStores stores) {
    return stores;
  }

  @Bean
  GovernanceApprovalPolicy governanceApprovalPolicy(
      @Value("${spider.governance.require-distinct-publisher:true}") boolean distinctPublisher,
      @Value("${spider.governance.require-distinct-activator:true}") boolean distinctActivator) {
    return new GovernanceApprovalPolicy(distinctPublisher, distinctActivator);
  }

  @Bean
  @Primary
  ActiveGovernanceSnapshotProviderPort activeGovernanceSnapshotProvider(
      GovernanceActivationStorePort activationStore,
      GovernanceSnapshotStorePort snapshotStore,
      GovernanceArtifactDigestService digestService,
      @Value("${spider.governance.scope:DEFAULT}") String scope,
      @Value("${spider.governance.control-plane.enabled:false}") boolean controlPlaneEnabled,
      @Value("${spider.governance.mode:STATIC}") String mode) {
    boolean cp =
        controlPlaneEnabled || GovernanceMode.CONTROL_PLANE.name().equalsIgnoreCase(mode);
    return new DefaultActiveGovernanceSnapshotProvider(
        activationStore, snapshotStore, digestService, new GovernanceScope(scope), cp);
  }
}
