package br.com.banco.spider.repository;

import br.com.banco.spider.model.ProductRoute;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

public interface ProductRouteRepository extends JpaRepository<ProductRoute, UUID> {

  List<ProductRoute> findByEnabledTrueOrderByProductCodeAscVersionDesc();

  Optional<ProductRoute> findFirstByProductCodeAndEnabledTrueOrderByVersionDesc(String productCode);
}
