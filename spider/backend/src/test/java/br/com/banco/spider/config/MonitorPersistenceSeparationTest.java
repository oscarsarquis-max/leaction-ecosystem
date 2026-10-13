package br.com.banco.spider.config;

import static org.assertj.core.api.Assertions.assertThat;
import static org.junit.jupiter.api.Assertions.assertTrue;

import br.com.banco.spider.infrastructure.persistence.jpa.JpaCanonicalPersistenceAdapters;
import br.com.banco.spider.infrastructure.persistence.jdbc.JdbcMonitorProjectionStoreAdapter;
import br.com.banco.spider.operational.monitor.MonitorProjectionPort;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import org.junit.jupiter.api.Test;
import org.springframework.boot.convert.ApplicationConversionService;
import org.springframework.boot.test.context.runner.ApplicationContextRunner;

class MonitorPersistenceSeparationTest {

  @Test
  void sandboxKeepsCanonicalMemoryAndDedicatedMonitorJdbc() throws Exception {
    String yaml = Files.readString(Path.of("src/main/resources/application-sandbox.yml"), StandardCharsets.UTF_8);
    assertTrue(yaml.contains("DataSourceAutoConfiguration"));
    assertTrue(yaml.contains("HibernateJpaAutoConfiguration"));
    assertTrue(yaml.contains("JpaRepositoriesAutoConfiguration"));
    assertTrue(yaml.contains("SPIDER_CANONICAL_PERSISTENCE_MODE:memory"));
    assertTrue(yaml.contains("SPIDER_MONITOR_PERSISTENCE_MODE:memory"));
    assertTrue(yaml.contains("SPIDER_MONITOR_JDBC_URL"));
  }

  @Test
  void jpaMonitorStoreDoesNotRequireCanonicalJpa() {
    new ApplicationContextRunner()
        .withInitializer(ctx -> ctx.getBeanFactory().setConversionService(ApplicationConversionService.getSharedInstance()))
        .withUserConfiguration(MonitorDataSourceConfig.class, MonitorProjectionConfig.class)
        .withPropertyValues(
            "spider.monitor.retention=P90D",
            "spider.monitor.persistence.mode=jpa",
            "spider.canonical.persistence.mode=memory",
            "spider.monitor.persistence.jdbc.url=jdbc:h2:mem:monitor-sep;MODE=PostgreSQL;DB_CLOSE_DELAY=-1",
            "spider.monitor.persistence.jdbc.username=sa",
            "spider.monitor.persistence.jdbc.password=",
            "spider.monitor.purge.enabled=false")
        .run(ctx -> {
          assertThat(ctx).hasSingleBean(MonitorProjectionPort.class);
          assertThat(ctx.getBean(MonitorProjectionPort.class))
              .isInstanceOf(JdbcMonitorProjectionStoreAdapter.class);
          assertThat(ctx.getBean(MonitorProjectionPort.class).isDurable()).isTrue();
          assertThat(ctx).hasBean("monitorDataSource");
          assertThat(ctx).doesNotHaveBean("dataSource");
          assertThat(ctx).doesNotHaveBean(JpaCanonicalPersistenceAdapters.ControlAdapter.class);
        });
  }

  @Test
  void jpaMonitorKeepsCanonicalDataSourcePrimaryWhenPresent() {
    new ApplicationContextRunner()
        .withInitializer(ctx -> ctx.getBeanFactory().setConversionService(ApplicationConversionService.getSharedInstance()))
        .withUserConfiguration(MonitorDataSourceConfig.class, MonitorProjectionConfig.class)
        .withPropertyValues(
            "spider.monitor.retention=P90D",
            "spider.monitor.persistence.mode=jpa",
            "spider.canonical.persistence.mode=memory",
            "spider.monitor.persistence.jdbc.url=jdbc:h2:mem:monitor-sep-jpa;MODE=PostgreSQL;DB_CLOSE_DELAY=-1",
            "spider.monitor.persistence.jdbc.username=sa",
            "spider.monitor.persistence.jdbc.password=",
            "spring.datasource.url=jdbc:h2:mem:canonical-sep;MODE=PostgreSQL;DB_CLOSE_DELAY=-1",
            "spring.datasource.username=sa",
            "spring.datasource.password=",
            "spring.datasource.driver-class-name=org.h2.Driver",
            "spider.monitor.purge.enabled=false")
        .run(ctx -> {
          assertThat(ctx).hasBean("monitorDataSource");
          assertThat(ctx).hasBean("dataSource");
          assertThat(ctx.getBean("dataSource", com.zaxxer.hikari.HikariDataSource.class).getPoolName())
              .isEqualTo("spider-primary");
          assertThat(ctx.getBean("monitorDataSource", com.zaxxer.hikari.HikariDataSource.class).getPoolName())
              .isEqualTo("spider-monitor");
        });
  }

  @Test
  void invalidMonitorModeFailsFast() {
    new ApplicationContextRunner()
        .withUserConfiguration(MonitorProjectionConfig.class)
        .withPropertyValues("spider.monitor.persistence.mode=flyway")
        .run(ctx -> assertThat(ctx).hasFailed());
  }
}
