package br.com.actionfinance.application.finance;

import java.time.LocalDate;
import java.util.UUID;

public record TitleWriteCommand(
        String description,
        UUID counterpartyId,
        String sourceReference,
        String amountMinor,
        String currency,
        LocalDate competenceDate,
        LocalDate dueDate,
        UUID categoryId,
        boolean register,
        Long expectedVersion,
        String reason) {}
