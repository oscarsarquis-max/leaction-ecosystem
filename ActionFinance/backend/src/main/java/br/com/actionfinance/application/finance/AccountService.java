package br.com.actionfinance.application.finance;

import br.com.actionfinance.application.ApplicationPrincipal;
import br.com.actionfinance.application.DemoPrincipalCatalog;
import br.com.actionfinance.application.finance.FinanceExceptions.IdempotencyConflictException;
import br.com.actionfinance.application.finance.FinanceExceptions.ValidationException;
import br.com.actionfinance.application.finance.FinanceExceptions.VersionConflictException;
import br.com.actionfinance.domain.AccountType;
import br.com.actionfinance.domain.MoneyAmount;
import br.com.actionfinance.infrastructure.persistence.JdbcAccountRepository;
import br.com.actionfinance.infrastructure.persistence.JdbcTitleRepository;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Isolation;
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
public class AccountService {

    private final CompanyAccessService access;
    private final JdbcAccountRepository accounts;
    private final JdbcTitleRepository titles;
    private final ObjectMapper mapper;
    private final Clock clock;

    public AccountService(
            CompanyAccessService access,
            JdbcAccountRepository accounts,
            JdbcTitleRepository titles,
            ObjectMapper mapper,
            Clock clock) {
        this.access = access;
        this.accounts = accounts;
        this.titles = titles;
        this.mapper = mapper;
        this.clock = clock;
    }

    public LocalDate businessDate() {
        return LocalDate.now(clock);
    }

    public List<AccountView> list(ApplicationPrincipal principal, UUID companyId) {
        access.requirePermission(principal, companyId, DemoPrincipalCatalog.PERMISSION_ACCOUNTS_READ);
        return accounts.list(readable(principal, companyId));
    }

    public AccountView get(ApplicationPrincipal principal, UUID companyId, UUID id) {
        access.requirePermission(principal, companyId, DemoPrincipalCatalog.PERMISSION_ACCOUNTS_READ);
        return accounts.find(readable(principal, companyId), id).orElseThrow(() -> new SecurityException("account-hidden"));
    }

    @Transactional(readOnly = true, isolation = Isolation.REPEATABLE_READ)
    public MovementView.Page movements(
            ApplicationPrincipal principal, UUID companyId, UUID id, LocalDate from, LocalDate to, int page, int size) {
        access.requirePermission(principal, companyId, DemoPrincipalCatalog.PERMISSION_ACCOUNTS_READ);
        AuthorizedScope scope = readable(principal, companyId);
        AccountView account = accounts.find(scope, id).orElseThrow(() -> new SecurityException("account-hidden"));
        LocalDate start = from == null ? account.openedOn() : from;
        LocalDate end = to == null ? businessDate() : to;
        if (start.isAfter(end)) {
            throw ValidationException.of("from", "O início do período não pode ser posterior ao fim.");
        }
        return accounts.listMovements(scope, id, start, end, page, size);
    }

    @Transactional
    public AccountView create(
            ApplicationPrincipal principal,
            UUID companyId,
            String name,
            String type,
            LocalDate openedOn,
            String openingBalanceMinor,
            String idempotencyKey) {
        AuthorizedScope scope = access.requireWritable(principal, companyId, DemoPrincipalCatalog.PERMISSION_ACCOUNTS_WRITE);
        String hash = hash("accounts.create", name, type, openedOn, openingBalanceMinor);
        return withIdempotency(scope, principal, "accounts.create", idempotencyKey, hash, () -> {
            Map<String, String> errors = new LinkedHashMap<>();
            String trimmed = name == null ? "" : name.trim();
            if (trimmed.isEmpty() || trimmed.length() > 100) {
                errors.put("name", "Nome é obrigatório e deve ter até 100 caracteres.");
            }
            AccountType parsedType = null;
            try {
                parsedType = AccountType.valueOf(type == null ? "" : type.trim().toUpperCase());
            } catch (IllegalArgumentException ex) {
                errors.put("type", "Informe Banco, Caixa físico ou Outra.");
            }
            if (openedOn == null) {
                errors.put("openedOn", "Informe a data de início do controle.");
            } else if (openedOn.isAfter(businessDate())) {
                errors.put("openedOn", "A data de início não pode ser futura.");
            }
            MoneyAmount opening = null;
            if (openingBalanceMinor == null || openingBalanceMinor.isBlank()) {
                errors.put("openingBalanceMinor", "Informe o saldo no início desse dia.");
            } else {
                try {
                    opening = MoneyAmount.parseSignedApi(openingBalanceMinor).orElse(null);
                    if (opening == null) {
                        errors.put("openingBalanceMinor", "Informe o saldo no início desse dia.");
                    }
                } catch (IllegalArgumentException ex) {
                    errors.put("openingBalanceMinor", "Informe o saldo em centavos, com sinal se negativo.");
                }
            }
            if (!errors.isEmpty()) {
                throw new ValidationException("Dados inválidos.", errors);
            }
            Instant now = Instant.now(clock);
            UUID id = UUID.randomUUID();
            CompanyView company = access.requireReadable(principal, companyId);
            AccountView created = new AccountView(
                    id,
                    scope.tenantId(),
                    scope.companyId(),
                    company.name(),
                    "CTA-" + id,
                    trimmed,
                    parsedType,
                    "BRL",
                    true,
                    openedOn,
                    opening.minorUnits(),
                    1L,
                    now,
                    now);
            accounts.insert(created, principal.actorId(), now);
            accounts.insertOpening(
                    scope,
                    UUID.randomUUID(),
                    id,
                    opening.minorUnits(),
                    openedOn,
                    now,
                    principal.actorId(),
                    "Saldo inicial informado");
            accounts.insertHistory(
                    UUID.randomUUID(),
                    scope,
                    id,
                    1L,
                    "CREATED",
                    principal.actorId(),
                    now,
                    toJson(Map.of(
                            "name", trimmed,
                            "type", parsedType.name(),
                            "openedOn", openedOn.toString(),
                            "openingBalanceMinor", opening.toApiString())));
            return accounts.find(scope, id).orElse(created);
        });
    }

    @Transactional
    public AccountView update(
            ApplicationPrincipal principal,
            UUID companyId,
            UUID id,
            String name,
            Boolean active,
            Long version,
            String idempotencyKey) {
        AuthorizedScope scope = access.requireWritable(principal, companyId, DemoPrincipalCatalog.PERMISSION_ACCOUNTS_WRITE);
        String hash = hash("accounts.update", id, name, active, version);
        return withIdempotency(scope, principal, "accounts.update", idempotencyKey, hash, () -> {
            if (version == null) {
                throw ValidationException.of("version", "Versão é obrigatória.");
            }
            AccountView current = accounts.lock(scope, id).orElseThrow(() -> new SecurityException("account-hidden"));
            if (current.version() != version) {
                throw new VersionConflictException("Esta conta foi alterada por outra pessoa.");
            }
            String trimmed = name == null ? null : name.trim();
            if (trimmed != null && (trimmed.isEmpty() || trimmed.length() > 100)) {
                throw ValidationException.of("name", "Nome é obrigatório e deve ter até 100 caracteres.");
            }
            Instant now = Instant.now(clock);
            if (accounts.update(scope, id, trimmed, active, version, now, principal.actorId()) != 1) {
                throw new VersionConflictException("Esta conta foi alterada por outra pessoa.");
            }
            String action = "RENAMED";
            if (active != null && active != current.active()) {
                action = Boolean.TRUE.equals(active) ? "REACTIVATED" : "DEACTIVATED";
            }
            accounts.insertHistory(
                    UUID.randomUUID(),
                    scope,
                    id,
                    version + 1,
                    action,
                    principal.actorId(),
                    now,
                    toJson(Map.of(
                            "name", Map.of("before", current.name(), "after", trimmed == null ? current.name() : trimmed),
                            "active", Map.of("before", current.active(), "after", active == null ? current.active() : active))));
            return accounts.find(scope, id).orElseThrow();
        });
    }

    private AccountView withIdempotency(
            AuthorizedScope scope,
            ApplicationPrincipal principal,
            String operation,
            String key,
            String hash,
            java.util.function.Supplier<AccountView> action) {
        if (key == null || key.isBlank() || key.length() > 128) {
            throw ValidationException.of("Idempotency-Key", "Informe uma chave de idempotência de até 128 caracteres.");
        }
        access.requireWritable(principal, scope.companyId(), DemoPrincipalCatalog.PERMISSION_ACCOUNTS_WRITE);
        titles.advisoryLock(scope, principal.actorId(), operation, key.trim());
        var existing = titles.findIdempotency(scope, principal.actorId(), operation, key.trim());
        if (existing.isPresent()) {
            if (!existing.get().requestHash().equals(hash)) {
                throw new IdempotencyConflictException();
            }
            return readStored(existing.get().bodyJson());
        }
        AccountView created = action.get();
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

    private AccountView readStored(String bodyJson) {
        try {
            return mapper.readValue(bodyJson, AccountView.class);
        } catch (JsonProcessingException e) {
            throw new IllegalStateException("idempotency-body", e);
        }
    }

    private AuthorizedScope readable(ApplicationPrincipal principal, UUID companyId) {
        CompanyView company = access.requireReadable(principal, companyId);
        return new AuthorizedScope(company.tenantId(), company.id());
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
}
