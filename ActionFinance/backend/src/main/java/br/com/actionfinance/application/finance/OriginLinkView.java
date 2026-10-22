package br.com.actionfinance.application.finance;

import java.time.Instant;

public record OriginLinkView(String originLabel, String provenance, Instant createdAt) {}
