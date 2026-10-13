package br.com.banco.spider.config;

import com.zaxxer.hikari.HikariConfig;
import com.zaxxer.hikari.HikariDataSource;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.context.annotation.Primary;
import org.springframework.util.StringUtils;

@Configuration
public class MonitorDataSourceConfig {

  @Configuration
  @ConditionalOnProperty(name = "spider.monitor.persistence.mode", havingValue = "jpa")
  static class PrimaryCanonicalDataSourceConfig {
    @Bean(name = "dataSource", destroyMethod = "close")
    @Primary
    @ConditionalOnProperty(name = "spring.datasource.url")
    HikariDataSource primaryDataSource(
        @Value("${spring.datasource.url}") String url,
        @Value("${spring.datasource.username:}") String username,
        @Value("${spring.datasource.password:}") String password,
        @Value("${spring.datasource.driver-class-name:}") String driver) {
      HikariConfig config = new HikariConfig();
      config.setJdbcUrl(url.trim());
      if (StringUtils.hasText(username)) {
        config.setUsername(username);
      }
      if (password != null) {
        config.setPassword(password);
      }
      if (StringUtils.hasText(driver)) {
        config.setDriverClassName(driver.trim());
      }
      config.setPoolName("spider-primary");
      config.setMaximumPoolSize(5);
      config.setMinimumIdle(0);
      config.setConnectionTimeout(10000);
      return new HikariDataSource(config);
    }
  }

  @Bean(name = "monitorDataSource", destroyMethod = "close")
  @ConditionalOnProperty(name = "spider.monitor.persistence.mode", havingValue = "jpa")
  HikariDataSource monitorDataSource(
      @Value("${spider.monitor.persistence.jdbc.url:}") String url,
      @Value("${spider.monitor.persistence.jdbc.username:}") String username,
      @Value("${spider.monitor.persistence.jdbc.password:}") String password,
      @Value("${spider.monitor.persistence.jdbc.max-pool-size:5}") int maxPoolSize,
      @Value("${spider.monitor.persistence.jdbc.connection-timeout:10000}") long connectionTimeout) {
    if (!StringUtils.hasText(url)) {
      throw new IllegalStateException(
          "spider.monitor.persistence.mode=jpa exige spider.monitor.persistence.jdbc.url. "
              + "Não ligue spider.canonical.persistence.mode para obter um DataSource.");
    }
    HikariConfig config = new HikariConfig();
    config.setJdbcUrl(url.trim());
    if (StringUtils.hasText(username)) {
      config.setUsername(username);
    }
    if (StringUtils.hasText(password)) {
      config.setPassword(password);
    }
    config.setPoolName("spider-monitor");
    config.setMaximumPoolSize(Math.max(1, maxPoolSize));
    config.setMinimumIdle(0);
    config.setConnectionTimeout(Math.max(1000, connectionTimeout));
    config.setInitializationFailTimeout(1);
    return new HikariDataSource(config);
  }
}
