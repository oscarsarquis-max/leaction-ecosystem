package br.com.banco.spider.config;

import javax.sql.DataSource;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.boot.actuate.health.Health;
import org.springframework.boot.actuate.health.HealthIndicator;
import org.springframework.boot.autoconfigure.condition.ConditionalOnBean;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Component;

/** Readiness do runtime: só o banco operacional. Não consulta o Monitor. */
@Component("operationalDb")
@ConditionalOnBean(name = "dataSource")
public class OperationalDbHealthIndicator implements HealthIndicator {

  private final DataSource dataSource;

  public OperationalDbHealthIndicator(@Qualifier("dataSource") DataSource dataSource) {
    this.dataSource = dataSource;
  }

  @Override
  public Health health() {
    try {
      Integer one = new JdbcTemplate(dataSource).queryForObject("select 1", Integer.class);
      if (one == null || one != 1) {
        return Health.down().withDetail("store", "ping-failed").build();
      }
      return Health.up().build();
    } catch (RuntimeException exception) {
      return Health.down().withDetail("store", "unavailable").build();
    }
  }
}
