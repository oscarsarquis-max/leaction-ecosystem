package br.com.actionfinance.application.finance;

import java.util.List;
import java.util.Optional;
import java.util.UUID;

public interface CompanyCatalog {

    Optional<CompanyView> findById(UUID companyId);

    List<CompanyView> findByIds(List<UUID> ids);
}
