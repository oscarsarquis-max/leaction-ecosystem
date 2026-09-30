package br.com.actionfinance.application.finance;

import br.com.actionfinance.application.ApplicationPrincipal;
import br.com.actionfinance.application.DemoPrincipalCatalog;
import br.com.actionfinance.application.finance.FinanceExceptions.AlreadyReversedException;
import br.com.actionfinance.application.finance.FinanceExceptions.IdempotencyConflictException;
import br.com.actionfinance.application.finance.FinanceExceptions.ValidationException;
import br.com.actionfinance.application.finance.FinanceExceptions.VersionConflictException;
import br.com.actionfinance.domain.HistoryAction;
import br.com.actionfinance.domain.MoneyAmount;
import br.com.actionfinance.domain.MovementKind;
import br.com.actionfinance.domain.SettlementMethod;
import br.com.actionfinance.domain.TitleDirection;
import br.com.actionfinance.domain.TitleStatus;
import br.com.actionfinance.infrastructure.persistence.JdbcAccountRepository;
import br.com.actionfinance.infrastructure.persistence.JdbcSettlementRepository;
import br.com.actionfinance.infrastructure.persistence.JdbcTitleRepository;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.math.BigDecimal;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.time.Clock;
import java.time.Instant;
import java.time.LocalDate;
import java.util.HexFormat;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;

@Service
public class SettlementService {

    private final CompanyAccessService access;
    private final JdbcTitleRepository titles;
    private final JdbcAccountRepository accounts;
    private final JdbcSettlementRepository settlements;
    private final ObjectMapper mapper;
    private final Clock clock;

    public SettlementService(
            CompanyAccessService access,
            JdbcTitleRepository titles,
            JdbcAccountRepository accounts,
            JdbcSettlementRepository settlements,
            ObjectMapper mapper,
            Clock clock) {
        this.access = access;
        this.titles = titles;
        this.accounts = accounts;
        this.settlements = settlements;
        this.mapper = mapper;
        this.clock = clock;
    }

    public LocalDate businessDate() {
        return LocalDate.now(clock);
    }

    public List<SettlementView> list(ApplicationPrincipal principal, UUID companyId, TitleDirection direction, UUID titleId) {
        access.requirePermission(principal, companyId, DemoPrincipalCatalog.PERMISSION_SETTLEMENTS_READ);
        TitleView title = titles.find(readable(principal, companyId), direction, titleId, businessDate())
                .orElseThrow(() -> new SecurityException("title-hidden"));
        return settlements.listForTitle(new AuthorizedScope(title.tenantId(), title.companyId()), title.id()).stream()
                .map(item -> withTitleBalances(item, title))
                .toList();
    }

    public SettlementView get(ApplicationPrincipal principal, UUID companyId, UUID id) {
        access.requirePermission(principal, companyId, DemoPrincipalCatalog.PERMISSION_SETTLEMENTS_READ);
        AuthorizedScope scope = readable(principal, companyId);
        SettlementView view = settlements.find(scope, id).orElseThrow(() -> new SecurityException("settlement-hidden"));
        TitleView title = titles.find(scope, view.direction(), view.titleId(), businessDate())
                .orElseThrow(() -> new SecurityException("settlement-hidden"));
        return withTitleBalances(view, title);
    }

    @Transactional
    public SettlementView record(
            ApplicationPrincipal principal,
            UUID companyId,
            TitleDirection direction,
            UUID titleId,
            UUID accountId,
            String amountMinor,
            LocalDate effectiveDate,
            String method,
            String note,
            Long expectedVersion,
            String idempotencyKey) {
        AuthorizedScope scope = access.requireWritable(principal, companyId, DemoPrincipalCatalog.PERMISSION_SETTLEMENTS_WRITE);
        String hash = hash(
                "settlements.record",
                direction,
                titleId,
                accountId,
                amountMinor,
                effectiveDate,
                method,
                note,
                expectedVersion);
        return withIdempotency(scope, principal, "settlements.record." + direction.name(), idempotencyKey, hash, () -> {
            TitleView title = titles.lock(scope, direction, titleId, businessDate())
                    .orElseThrow(() -> new SecurityException("title-hidden"));
            AccountView account = accounts.lock(scope, accountId).orElseThrow(
                    () -> ValidationException.of("accountId", "Conta financeira não encontrada nesta empresa."));
            Map<String, String> errors = new LinkedHashMap<>();
            if (title.status() != TitleStatus.OPEN) {
                errors.put("status", "Somente título em aberto pode receber baixa.");
            }
            if (!account.active()) {
                errors.put("accountId", "Conta inativa não recebe nova baixa.");
            }
            if (!"BRL".equals(account.currency()) || !"BRL".equals(title.currency())) {
                errors.put("currency", "A conta e o título precisam estar em BRL.");
            }
            MoneyAmount amount = null;
            if (amountMinor == null || amountMinor.isBlank()) {
                errors.put("amountMinor", "Informe um valor positivo.");
            } else {
                try {
                    amount = MoneyAmount.parseApi(amountMinor).orElse(null);
                    if (amount == null) {
                        errors.put("amountMinor", "Informe um valor positivo.");
                    }
                } catch (IllegalArgumentException ex) {
                    errors.put("amountMinor", "Informe um valor inteiro positivo em centavos, somente dígitos.");
                }
            }
            if (effectiveDate == null) {
                errors.put("effectiveDate", "Informe a data efetiva.");
            } else if (effectiveDate.isAfter(businessDate())) {
                errors.put("effectiveDate", "A data efetiva não pode ser futura.");
            } else if (effectiveDate.isBefore(account.openedOn())) {
                errors.put("effectiveDate", "A data efetiva não pode ser anterior à abertura da conta.");
            }
            SettlementMethod parsedMethod = null;
            try {
                parsedMethod = SettlementMethod.valueOf(method == null ? "" : method.trim().toUpperCase());
            } catch (IllegalArgumentException ex) {
                errors.put("method", "Informe o meio de recebimento ou pagamento.");
            }
            String trimmedNote = note == null || note.isBlank() ? null : note.trim();
            if (trimmedNote != null && trimmedNote.length() > 500) {
                errors.put("note", "Observação deve ter até 500 caracteres.");
            }
            if (expectedVersion == null || expectedVersion != title.version()) {
                throw new VersionConflictException(
                        "Este título foi alterado por outra pessoa. Revise o restante atual.",
                        Map.of(
                                "outstandingAmountMinor",
                                title.outstandingAmountMinor() == null
                                        ? "0"
                                        : title.outstandingAmountMinor().toPlainString()));
            }
            if (amount != null && title.outstandingAmountMinor() != null
                    && amount.minorUnits().compareTo(title.outstandingAmountMinor()) > 0) {
                errors.put(
                        "amountMinor",
                        "O valor não pode ser maior que o restante de "
                                + title.outstandingAmountMinor().toPlainString()
                                + " centavos.");
            }
            if (!errors.isEmpty()) {
                throw new ValidationException("Dados inválidos.", errors);
            }
            Instant now = Instant.now(clock);
            UUID settlementId = UUID.randomUUID();
            BigDecimal signed = direction == TitleDirection.RECEIVABLE
                    ? amount.minorUnits()
                    : amount.minorUnits().negate();
            settlements.insertSettlement(
                    settlementId,
                    scope,
                    account.id(),
                    direction,
                    amount.minorUnits(),
                    effectiveDate,
                    parsedMethod,
                    trimmedNote,
                    now,
                    principal.actorId(),
                    clipName(principal.displayName()));
            settlements.insertAllocation(UUID.randomUUID(), scope, settlementId, title.id(), amount.minorUnits());
            accounts.insertMovement(
                    UUID.randomUUID(),
                    scope,
                    account.id(),
                    MovementKind.SETTLEMENT,
                    signed,
                    effectiveDate,
                    now,
                    principal.actorId(),
                    settlementId,
                    null,
                    movementDescription(direction, title.reference(), false));
            if (settlements.bumpTitleVersion(scope, title.id(), title.version(), now, principal.actorId()) != 1) {
                throw new VersionConflictException(
                        "Este título foi alterado por outra pessoa. Revise o restante atual.",
                        Map.of(
                                "outstandingAmountMinor",
                                title.outstandingAmountMinor().toPlainString()));
            }
            TitleView after = titles.find(scope, direction, title.id(), businessDate()).orElseThrow();
            titles.insertHistory(
                    UUID.randomUUID(),
                    after,
                    HistoryAction.SETTLEMENT_RECORDED,
                    principal.actorId(),
                    clipName(principal.displayName()),
                    now,
                    trimmedNote,
                    toJson(Map.of(
                            "settlementId", settlementId.toString(),
                            "accountId", account.id().toString(),
                            "accountName", account.name(),
                            "amountMinor", amount.toApiString(),
                            "effectiveDate", effectiveDate.toString(),
                            "method", parsedMethod.name(),
                            "settledAmountMinor",
                            Map.of(
                                    "before", title.settledAmountMinor().toPlainString(),
                                    "after", after.settledAmountMinor().toPlainString()),
                            "outstandingAmountMinor",
                            Map.of(
                                    "before", title.outstandingAmountMinor().toPlainString(),
                                    "after", after.outstandingAmountMinor().toPlainString()))));
            return withTitleBalances(settlements.find(scope, settlementId).orElseThrow(), after);
        });
    }

    @Transactional
    public SettlementView reverse(
            ApplicationPrincipal principal,
            UUID companyId,
            UUID settlementId,
            LocalDate effectiveDate,
            String reason,
            Long expectedVersion,
            String idempotencyKey) {
        AuthorizedScope scope = access.requireWritable(principal, companyId, DemoPrincipalCatalog.PERMISSION_SETTLEMENTS_REVERSE);
        String hash = hash("settlements.reverse", settlementId, effectiveDate, reason, expectedVersion);
        return withIdempotency(scope, principal, "settlements.reverse", idempotencyKey, hash, () -> {
            SettlementView current = settlements.find(scope, settlementId)
                    .orElseThrow(() -> new SecurityException("settlement-hidden"));
            TitleView title = titles.lock(scope, current.direction(), current.titleId(), businessDate())
                    .orElseThrow(() -> new SecurityException("settlement-hidden"));
            AccountView account = accounts.lock(scope, current.accountId())
                    .orElseThrow(() -> new SecurityException("settlement-hidden"));
            if (current.reversed()) {
                throw new AlreadyReversedException();
            }
            if (expectedVersion == null || expectedVersion != title.version()) {
                throw new VersionConflictException(
                        "Este título foi alterado por outra pessoa. Revise o restante atual.",
                        Map.of(
                                "outstandingAmountMinor",
                                title.outstandingAmountMinor() == null
                                        ? "0"
                                        : title.outstandingAmountMinor().toPlainString()));
            }
            String trimmed = reason == null ? "" : reason.trim();
            if (trimmed.length() < 3 || trimmed.length() > 500) {
                throw ValidationException.of("reason", "Motivo deve ter entre 3 e 500 caracteres.");
            }
            if (effectiveDate == null) {
                throw ValidationException.of("effectiveDate", "Informe a data do estorno.");
            }
            if (effectiveDate.isBefore(current.effectiveDate())) {
                throw ValidationException.of("effectiveDate", "A data do estorno não pode ser anterior à da baixa.");
            }
            if (effectiveDate.isAfter(businessDate())) {
                throw ValidationException.of("effectiveDate", "A data do estorno não pode ser futura.");
            }
            Instant now = Instant.now(clock);
            UUID reversalId = UUID.randomUUID();
            BigDecimal opposite = current.direction() == TitleDirection.RECEIVABLE
                    ? current.amountMinor().negate()
                    : current.amountMinor();
            settlements.insertReversal(
                    reversalId,
                    scope,
                    current.id(),
                    effectiveDate,
                    trimmed,
                    now,
                    principal.actorId(),
                    clipName(principal.displayName()));
            accounts.insertMovement(
                    UUID.randomUUID(),
                    scope,
                    account.id(),
                    MovementKind.REVERSAL,
                    opposite,
                    effectiveDate,
                    now,
                    principal.actorId(),
                    current.id(),
                    reversalId,
                    movementDescription(current.direction(), title.reference(), true));
            if (settlements.bumpTitleVersion(scope, title.id(), title.version(), now, principal.actorId()) != 1) {
                throw new VersionConflictException();
            }
            TitleView after = titles.find(scope, title.direction(), title.id(), businessDate()).orElseThrow();
            titles.insertHistory(
                    UUID.randomUUID(),
                    after,
                    HistoryAction.SETTLEMENT_REVERSED,
                    principal.actorId(),
                    clipName(principal.displayName()),
                    now,
                    trimmed,
                    toJson(Map.of(
                            "settlementId", current.id().toString(),
                            "reversalId", reversalId.toString(),
                            "accountId", account.id().toString(),
                            "amountMinor", current.amountMinor().toPlainString(),
                            "effectiveDate", effectiveDate.toString(),
                            "settledAmountMinor",
                            Map.of(
                                    "before", title.settledAmountMinor().toPlainString(),
                                    "after", after.settledAmountMinor().toPlainString()),
                            "outstandingAmountMinor",
                            Map.of(
                                    "before", title.outstandingAmountMinor().toPlainString(),
                                    "after", after.outstandingAmountMinor().toPlainString()))));
            return withTitleBalances(settlements.find(scope, current.id()).orElseThrow(), after);
        });
    }

    private SettlementView withIdempotency(
            AuthorizedScope scope,
            ApplicationPrincipal principal,
            String operation,
            String key,
            String hash,
            java.util.function.Supplier<SettlementView> action) {
        if (key == null || key.isBlank() || key.length() > 128) {
            throw ValidationException.of("Idempotency-Key", "Informe uma chave de idempotência de até 128 caracteres.");
        }
        String required =
                operation.startsWith("settlements.reverse")
                        ? DemoPrincipalCatalog.PERMISSION_SETTLEMENTS_REVERSE
                        : DemoPrincipalCatalog.PERMISSION_SETTLEMENTS_WRITE;
        access.requireWritable(principal, scope.companyId(), required);
        titles.advisoryLock(scope, principal.actorId(), operation, key.trim());
        var existing = titles.findIdempotency(scope, principal.actorId(), operation, key.trim());
        if (existing.isPresent()) {
            if (!existing.get().requestHash().equals(hash)) {
                throw new IdempotencyConflictException();
            }
            return readStored(existing.get().bodyJson());
        }
        SettlementView created = action.get();
        titles.insertIdempotency(
                UUID.randomUUID(),
                scope,
                principal.actorId(),
                operation,
                key.trim(),
                hash,
                created.id(),
                200,
                toJson(created),
                Instant.now(clock));
        return created;
    }

    private SettlementView readStored(String bodyJson) {
        try {
            return mapper.readValue(bodyJson, SettlementView.class);
        } catch (JsonProcessingException e) {
            throw new IllegalStateException("idempotency-body", e);
        }
    }

    private AuthorizedScope readable(ApplicationPrincipal principal, UUID companyId) {
        CompanyView company = access.requireReadable(principal, companyId);
        return new AuthorizedScope(company.tenantId(), company.id());
    }

    private static SettlementView withTitleBalances(SettlementView view, TitleView title) {
        return new SettlementView(
                view.id(),
                view.tenantId(),
                view.companyId(),
                view.titleId(),
                view.titleReference(),
                view.titleDescription(),
                view.counterpartyName(),
                view.direction(),
                view.accountId(),
                view.accountName(),
                view.accountActive(),
                view.amountMinor(),
                view.currency(),
                view.effectiveDate(),
                view.method(),
                view.note(),
                view.originKind(),
                view.recordedAt(),
                view.recordedBy(),
                view.actorDisplayName(),
                view.reversed(),
                view.reversalId(),
                view.reversalEffectiveDate(),
                view.reversalReason(),
                view.reversalRecordedAt(),
                view.reversalActorDisplayName(),
                view.movementId(),
                view.reversalMovementId(),
                title.settledAmountMinor(),
                title.outstandingAmountMinor(),
                title.version());
    }

    private static String movementDescription(TitleDirection direction, String reference, boolean reversal) {
        String base = direction == TitleDirection.RECEIVABLE ? "Recebimento registrado" : "Pagamento registrado";
        if (reversal) {
            base = "Estorno do registro";
        }
        return (base + " · " + reference).length() > 200 ? (base + " · " + reference).substring(0, 200) : base + " · " + reference;
    }


    private String toJson(Object value) {
        try {
            return mapper.writeValueAsString(value);
        } catch (JsonProcessingException e) {
            throw new IllegalStateException("json", e);
        }
    }

    private String hash(Object... parts) {
        try {
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            digest.update(toJson(java.util.Arrays.asList(parts)).getBytes(StandardCharsets.UTF_8));
            return HexFormat.of().formatHex(digest.digest());
        } catch (Exception e) {
            throw new IllegalStateException(e);
        }
    }

    private static String clipName(String name) {
        if (name == null || name.isBlank()) {
            return "Operador local";
        }
        return name.length() > 160 ? name.substring(0, 160) : name;
    }
}
