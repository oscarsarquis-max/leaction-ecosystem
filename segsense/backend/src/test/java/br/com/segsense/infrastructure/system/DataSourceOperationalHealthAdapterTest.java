package br.com.segsense.infrastructure.system;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

import br.com.segsense.domain.system.OperationalState;
import java.sql.Connection;
import javax.sql.DataSource;
import org.junit.jupiter.api.Test;

class DataSourceOperationalHealthAdapterTest {

  @Test
  void reportsUpWhenDatabaseConnectionIsValid() throws Exception {
    DataSource dataSource = mock(DataSource.class);
    Connection connection = mock(Connection.class);
    when(dataSource.getConnection()).thenReturn(connection);
    when(connection.isValid(2)).thenReturn(true);

    DataSourceOperationalHealthAdapter adapter = new DataSourceOperationalHealthAdapter(dataSource);

    assertThat(adapter.currentState()).isEqualTo(OperationalState.UP);
  }

  @Test
  void reportsDegradedWhenDatabaseConnectionFails() throws Exception {
    DataSource dataSource = mock(DataSource.class);
    when(dataSource.getConnection()).thenThrow(new java.sql.SQLException("unavailable"));

    DataSourceOperationalHealthAdapter adapter = new DataSourceOperationalHealthAdapter(dataSource);

    assertThat(adapter.currentState()).isEqualTo(OperationalState.DEGRADED);
  }
}
