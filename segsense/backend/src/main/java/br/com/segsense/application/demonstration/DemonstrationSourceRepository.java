package br.com.segsense.application.demonstration;

import br.com.segsense.domain.demonstration.DemonstrationSource;
import java.util.List;
import java.util.Optional;
import java.util.UUID;

public interface DemonstrationSourceRepository {

  List<DemonstrationSource> listAll();

  Optional<DemonstrationSource> findById(UUID id);

  Optional<DemonstrationSource> findByKey(String key);
}
