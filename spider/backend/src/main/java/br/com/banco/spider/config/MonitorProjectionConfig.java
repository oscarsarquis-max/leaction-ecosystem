package br.com.banco.spider.config;

import br.com.banco.spider.infrastructure.persistence.jdbc.JdbcMonitorProjectionStoreAdapter;
import br.com.banco.spider.infrastructure.persistence.jdbc.MonitorSchemaMigrator;
import br.com.banco.spider.infrastructure.persistence.memory.InMemoryMonitorProjectionStore;
import br.com.banco.spider.operational.monitor.MonitorProjectionPort;
import br.com.banco.spider.operational.monitor.MonitorProjectionService;
import java.time.Clock;
import java.time.Duration;
import java.util.Locale;
import java.util.Set;
import javax.sql.DataSource;
import org.springframework.beans.factory.ObjectProvider;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.scheduling.annotation.EnableScheduling;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.util.StringUtils;

@Configuration
@EnableScheduling
public class MonitorProjectionConfig {

  private static final Set<String> MODES = Set.of("memory", "jpa");

  public MonitorProjectionConfig(
      @Value("${spider.monitor.persistence.mode:memory}") String mode) {
    String normalized = mode == null ? "" : mode.trim().toLowerCase(Locale.ROOT);
    if (!MODES.contains(normalized)) {
      throw new IllegalStateException(
          "spider.monitor.persistence.mode inválido. Use memory ou jpa.");
    }
  }

  @Bean
  @ConditionalOnProperty(name = "spider.monitor.persistence.mode", havingValue = "memory", matchIfMissing = true)
  MonitorProjectionPort inMemoryMonitorProjectionStore() {
    return new InMemoryMonitorProjectionStore();
  }

  @Bean
  @ConditionalOnProperty(name = "spider.monitor.persistence.mode", havingValue = "jpa")
  MonitorSchemaMigrator monitorSchemaMigrator(
      @Qualifier("monitorDataSource") DataSource monitorDataSource) {
    MonitorSchemaMigrator migrator = new MonitorSchemaMigrator(new JdbcTemplate(monitorDataSource));
    migrator.migrate();
    return migrator;
  }

  @Bean
  @ConditionalOnProperty(name = "spider.monitor.persistence.mode", havingValue = "jpa")
  MonitorProjectionPort jdbcMonitorProjectionStore(
      @Qualifier("monitorDataSource") DataSource monitorDataSource, MonitorSchemaMigrator migrator) {
    if (migrator == null) {
      throw new IllegalStateException("Migrator do Monitor não inicializado.");
    }
    return new JdbcMonitorProjectionStoreAdapter(new JdbcTemplate(monitorDataSource));
  }

  @Bean
  MonitorProjectionService monitorProjectionService(
      ObjectProvider<MonitorProjectionPort> store,
      @Value("${spider.monitor.retention:P90D}") Duration retention) {
    MonitorProjectionPort port = store.getIfAvailable();
    return port == null
        ? new MonitorProjectionService(null, retention, Clock.systemUTC())
        : new MonitorProjectionService(port, retention, Clock.systemUTC());
  }

  @Bean
  @ConditionalOnProperty(name = "spider.monitor.purge.enabled", havingValue = "true", matchIfMissing = true)
  MonitorProjectionPurgeJob monitorProjectionPurgeJob(MonitorProjectionService service) {
    return new MonitorProjectionPurgeJob(service);
  }

  public static final class MonitorProjectionPurgeJob {
    private final MonitorProjectionService service;

    MonitorProjectionPurgeJob(MonitorProjectionService service) {
      this.service = service;
    }

    @Scheduled(fixedDelayString = "${spider.monitor.purge.interval:PT1H}")
    public void purge() {
      int removed = service.purgeExpired();
      if (removed > 0) {
        org.slf4j.LoggerFactory.getLogger(MonitorProjectionPurgeJob.class)
            .info("event=monitor_projection_purged removed={}", removed);
      }
    }
  }

  static void validateMode(String mode) {
    if (!StringUtils.hasText(mode) || !MODES.contains(mode.trim().toLowerCase(Locale.ROOT))) {
      throw new IllegalStateException("spider.monitor.persistence.mode inválido. Use memory ou jpa.");
    }
  }
}
