package br.com.segsense.application.system;

import br.com.segsense.domain.system.OperationalState;

public interface OperationalHealthPort {

  OperationalState currentState();
}
