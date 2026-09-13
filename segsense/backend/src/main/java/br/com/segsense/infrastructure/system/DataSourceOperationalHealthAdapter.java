package br.com.segsense.infrastructure.system;

import br.com.segsense.application.system.OperationalHealthPort;
import br.com.segsense.domain.system.OperationalState;
import java.sql.Connection;
import javax.sql.DataSource;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Component;

@Component
public class DataSourceOperationalHealthAdapter implements OperationalHealthPort {

  private static final Logger log = LoggerFactory.getLogger(DataSourceOperationalHealthAdapter.class);

  private final DataSource dataSource;

  public DataSourceOperationalHealthAdapter(DataSource dataSource) {
    this.dataSource = dataSource;
  }

  @Override
  public OperationalState currentState() {
    try (Connection connection = dataSource.getConnection()) {
      if (connection.isValid(2)) {
        return OperationalState.UP;
      }
      return OperationalState.DEGRADED;
    } catch (Exception exception) {
      log.warn("event=local_operational_health_degraded");
      return OperationalState.DEGRADED;
    }
  }
}
