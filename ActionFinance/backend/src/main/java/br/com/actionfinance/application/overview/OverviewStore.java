package br.com.actionfinance.application.overview;

import br.com.actionfinance.application.finance.AuthorizedScope;

import java.time.Instant;
import java.time.LocalDate;

public interface OverviewStore {

    OverviewFacts load(AuthorizedScope scope, Instant from, Instant toExclusive, LocalDate fromDay, LocalDate toDay, LocalDate today);
}
