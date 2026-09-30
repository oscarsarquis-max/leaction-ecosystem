package br.com.actionfinance.application.finance;

import br.com.actionfinance.application.ApplicationPrincipal;
import br.com.actionfinance.application.DemoPrincipalCatalog;
import br.com.actionfinance.application.finance.CatalogRecords.CategoryView;
import br.com.actionfinance.application.finance.CatalogRecords.CounterpartyView;
import br.com.actionfinance.application.finance.FinanceExceptions.IdempotencyConflictException;
import br.com.actionfinance.application.finance.FinanceExceptions.ValidationException;
import br.com.actionfinance.application.finance.FinanceExceptions.VersionConflictException;
import br.com.actionfinance.domain.HistoryAction;
import br.com.actionfinance.domain.MoneyAmount;
import br.com.actionfinance.domain.OriginKind;
import br.com.actionfinance.domain.SettlementStatus;
import br.com.actionfinance.domain.TitleDirection;
import br.com.actionfinance.domain.TitleStatus;
import br.com.actionfinance.infrastructure.persistence.JdbcCatalogRepository;
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
import java.util.ArrayList;
import java.util.HexFormat;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;

@Service
public class TitleService {

    private final CompanyAccessService access;
    private final JdbcTitleRepository titles;
    private final JdbcCatalogRepository catalogs;
    private final ObjectMapper mapper;
    private final Clock clock;

    public TitleService(
            CompanyAccessService access,
            JdbcTitleRepository titles,
            JdbcCatalogRepository catalogs,
            ObjectMapper mapper,
            Clock clock) {
        this.access = access;
        this.titles = titles;
        this.catalogs = catalogs;
        this.mapper = mapper;
        this.clock = clock;
    }

    public LocalDate businessDate() {
        return LocalDate.now(clock);
    }

    @Transactional(readOnly = true, isolation = Isolation.REPEATABLE_READ)
    public TitleView.Page list(
            ApplicationPrincipal principal, UUID companyId, TitleDirection direction, TitleListQuery query) {
        AuthorizedScope scope = readable(principal, companyId);
        return titles.list(scope, direction, query, businessDate());
    }

    public TitleView get(ApplicationPrincipal principal, UUID companyId, TitleDirection direction, UUID id) {
        return titles.find(readable(principal, companyId), direction, id, businessDate())
                .orElseThrow(() -> new SecurityException("title-hidden"));
    }

    public List<TitleView.HistoryEntry> history(
            ApplicationPrincipal principal, UUID companyId, TitleDirection direction, UUID id) {
        TitleView title = get(principal, companyId, direction, id);
        return titles.history(new AuthorizedScope(title.tenantId(), title.companyId()), title.id());
    }

    @Transactional
    public TitleView create(
            ApplicationPrincipal principal,
            UUID companyId,
            TitleDirection direction,
            TitleWriteCommand command,
            String idempotencyKey) {
        AuthorizedScope scope = access.requireWritable(principal, companyId, DemoPrincipalCatalog.PERMISSION_TITLES_WRITE);
        String hash = hash("titles.create", direction, command);
        return withIdempotency(scope, principal, "titles.create." + direction.name(), idempotencyKey, hash, () -> {
            ParsedFields fields = parse(command, command.register());
            if (command.register()) {
                requireComplete(fields);
            }
            Instant now = Instant.now(clock);
            UUID id = UUID.randomUUID();
            String prefix = direction == TitleDirection.RECEIVABLE ? "REC-" : "PAG-";
            CatalogSnapshot catalogsSnap = resolveCatalogs(scope, direction, fields, command.register(), null);
            TitleStatus status = command.register() ? TitleStatus.OPEN : TitleStatus.DRAFT;
            TitleView created = new TitleView(
                    id,
                    scope.tenantId(),
                    scope.companyId(),
                    prefix + id,
                    direction,
                    status,
                    fields.description,
                    catalogsSnap.counterparty() == null ? null : catalogsSnap.counterparty().id(),
                    catalogsSnap.counterparty() == null ? null : catalogsSnap.counterparty().code(),
                    catalogsSnap.counterparty() == null ? null : catalogsSnap.counterparty().name(),
                    catalogsSnap.counterparty() == null || catalogsSnap.counterparty().active(),
                    catalogsSnap.category() == null ? null : catalogsSnap.category().id(),
                    catalogsSnap.category() == null ? null : catalogsSnap.category().code(),
                    catalogsSnap.category() == null ? null : catalogsSnap.category().name(),
                    catalogsSnap.category() == null || catalogsSnap.category().active(),
                    fields.amount == null ? null : fields.amount.minorUnits(),
                    "BRL",
                    fields.competence,
                    fields.due,
                    false,
                    OriginKind.MANUAL,
                    fields.sourceReference,
                    1L,
                    now,
                    now,
                    principal.actorId(),
                    principal.actorId(),
                    command.register() ? now : null,
                    null,
                    null,
                    access.requireReadable(principal, companyId).demo(),
                    BigDecimal.ZERO,
                    fields.amount == null ? BigDecimal.ZERO : fields.amount.minorUnits(),
                    SettlementStatus.derive(status, fields.amount == null ? null : fields.amount.minorUnits(), BigDecimal.ZERO));
            titles.insert(created);
            titles.insertHistory(
                    UUID.randomUUID(),
                    created,
                    HistoryAction.CREATED,
                    principal.actorId(),
                    clipName(principal.displayName()),
                    now,
                    null,
                    changesJson(snapshot(null), snapshot(created)));
            return created;
        });
    }

    @Transactional
    public TitleView update(
            ApplicationPrincipal principal,
            UUID companyId,
            TitleDirection direction,
            UUID id,
            TitleWriteCommand command,
            String idempotencyKey) {
        AuthorizedScope scope = access.requireWritable(principal, companyId, DemoPrincipalCatalog.PERMISSION_TITLES_WRITE);
        String hash = hash("titles.update", direction, id, command);
        return withIdempotency(scope, principal, "titles.update." + direction.name(), idempotencyKey, hash, () -> {
            TitleView current = titles.lock(scope, direction, id, businessDate())
                    .orElseThrow(() -> new SecurityException("title-hidden"));
            if (command.expectedVersion() == null || command.expectedVersion() != current.version()) {
                throw new VersionConflictException();
            }
            if (current.status() == TitleStatus.CANCELLED) {
                throw ValidationException.of("status", "Título cancelado não pode ser alterado.");
            }
            boolean correctingOpen = current.status() == TitleStatus.OPEN;
            if (titles.hasSettlementHistory(scope, current.id())
                    && mutatingProtectedFields(current, command)) {
                throw ValidationException.of(
                        "amountMinor",
                        "Este título já possui registro de baixa. Estorne as baixas e cancele ou substitua o título para alterar valor, contraparte ou competência.");
            }
            if (correctingOpen && (command.reason() == null || command.reason().trim().length() < 3)) {
                throw ValidationException.of("reason", "Informe o motivo da correção (3 a 500 caracteres).");
            }
            boolean registering = command.register() && current.status() == TitleStatus.DRAFT;
            if (registering && correctingOpen) {
                throw ValidationException.of("status", "Título aberto não pode ser registrado novamente.");
            }
            ParsedFields fields = parse(command, correctingOpen || registering);
            if (correctingOpen || registering) {
                requireComplete(fields);
            }
            CatalogSnapshot catalogsSnap = resolveCatalogs(scope, direction, fields, correctingOpen || registering, current);
            Instant now = Instant.now(clock);
            TitleStatus nextStatus = registering ? TitleStatus.OPEN : current.status();
            Instant confirmedAt = registering ? now : current.confirmedAt();
            HistoryAction historyAction = registering ? HistoryAction.CONFIRMED : HistoryAction.UPDATED;
            TitleView updated = new TitleView(
                    current.id(),
                    current.tenantId(),
                    current.companyId(),
                    current.reference(),
                    current.direction(),
                    nextStatus,
                    fields.description,
                    catalogsSnap.counterparty() == null ? null : catalogsSnap.counterparty().id(),
                    catalogsSnap.counterparty() == null ? null : catalogsSnap.counterparty().code(),
                    catalogsSnap.counterparty() == null ? null : catalogsSnap.counterparty().name(),
                    catalogsSnap.counterparty() == null || catalogsSnap.counterparty().active(),
                    catalogsSnap.category() == null ? null : catalogsSnap.category().id(),
                    catalogsSnap.category() == null ? null : catalogsSnap.category().code(),
                    catalogsSnap.category() == null ? null : catalogsSnap.category().name(),
                    catalogsSnap.category() == null || catalogsSnap.category().active(),
                    fields.amount == null ? null : fields.amount.minorUnits(),
                    current.currency(),
                    fields.competence,
                    fields.due,
                    false,
                    current.originKind(),
                    fields.sourceReference,
                    current.version() + 1,
                    current.createdAt(),
                    now,
                    current.createdBy(),
                    principal.actorId(),
                    confirmedAt,
                    current.cancelledAt(),
                    current.cancellationReason(),
                    current.companyDemo(),
                    current.settledAmountMinor(),
                    current.outstandingAmountMinor(),
                    current.settlementStatus());
            if (titles.update(updated, current.version()) != 1) {
                throw new VersionConflictException();
            }
            titles.insertHistory(
                    UUID.randomUUID(),
                    updated,
                    historyAction,
                    principal.actorId(),
                    clipName(principal.displayName()),
                    now,
                    correctingOpen ? command.reason().trim() : null,
                    changesJson(snapshot(current), snapshot(updated)));
            return updated;
        });
    }

    @Transactional
    public TitleView confirm(
            ApplicationPrincipal principal, UUID companyId, TitleDirection direction, UUID id, long version, String idempotencyKey) {
        AuthorizedScope scope = access.requireWritable(principal, companyId, DemoPrincipalCatalog.PERMISSION_TITLES_WRITE);
        String hash = hash("titles.confirm", direction, id, version);
        return withIdempotency(scope, principal, "titles.confirm." + direction.name(), idempotencyKey, hash, () -> {
            TitleView current = titles.lock(scope, direction, id, businessDate())
                    .orElseThrow(() -> new SecurityException("title-hidden"));
            if (version != current.version()) {
                throw new VersionConflictException();
            }
            if (current.status() != TitleStatus.DRAFT) {
                throw ValidationException.of("status", "Somente rascunho pode ser confirmado.");
            }
            TitleWriteCommand asCommand = new TitleWriteCommand(
                    current.description(),
                    current.counterpartyId(),
                    current.sourceReference(),
                    current.amountMinor() == null ? null : current.amountMinor().toPlainString(),
                    current.currency(),
                    current.competenceDate(),
                    current.dueDate(),
                    current.categoryId(),
                    true,
                    version,
                    null);
            ParsedFields fields = parse(asCommand, true);
            requireComplete(fields);
            CatalogSnapshot catalogsSnap = resolveCatalogs(scope, direction, fields, true, null);
            Instant now = Instant.now(clock);
            TitleView updated = new TitleView(
                    current.id(),
                    current.tenantId(),
                    current.companyId(),
                    current.reference(),
                    current.direction(),
                    TitleStatus.OPEN,
                    fields.description,
                    catalogsSnap.counterparty().id(),
                    catalogsSnap.counterparty().code(),
                    catalogsSnap.counterparty().name(),
                    catalogsSnap.counterparty().active(),
                    catalogsSnap.category().id(),
                    catalogsSnap.category().code(),
                    catalogsSnap.category().name(),
                    catalogsSnap.category().active(),
                    fields.amount.minorUnits(),
                    current.currency(),
                    fields.competence,
                    fields.due,
                    false,
                    current.originKind(),
                    fields.sourceReference,
                    current.version() + 1,
                    current.createdAt(),
                    now,
                    current.createdBy(),
                    principal.actorId(),
                    now,
                    null,
                    null,
                    current.companyDemo(),
                    BigDecimal.ZERO,
                    fields.amount.minorUnits(),
                    SettlementStatus.UNSETTLED);
            if (titles.update(updated, current.version()) != 1) {
                throw new VersionConflictException();
            }
            titles.insertHistory(
                    UUID.randomUUID(),
                    updated,
                    HistoryAction.CONFIRMED,
                    principal.actorId(),
                    clipName(principal.displayName()),
                    now,
                    null,
                    changesJson(snapshot(current), snapshot(updated)));
            return updated;
        });
    }

    @Transactional
    public TitleView cancel(
            ApplicationPrincipal principal,
            UUID companyId,
            TitleDirection direction,
            UUID id,
            long version,
            String reason,
            String idempotencyKey) {
        AuthorizedScope scope = access.requireWritable(principal, companyId, DemoPrincipalCatalog.PERMISSION_TITLES_WRITE);
        String hash = hash("titles.cancel", direction, id, version, reason);
        return withIdempotency(scope, principal, "titles.cancel." + direction.name(), idempotencyKey, hash, () -> {
            TitleView current = titles.lock(scope, direction, id, businessDate())
                    .orElseThrow(() -> new SecurityException("title-hidden"));
            if (version != current.version()) {
                throw new VersionConflictException();
            }
            if (current.status() == TitleStatus.CANCELLED) {
                throw ValidationException.of("status", "Título já cancelado.");
            }
            if (current.settledAmountMinor() != null && current.settledAmountMinor().signum() > 0) {
                throw ValidationException.of(
                        "status", "Estorne os registros de baixa antes de cancelar este título.");
            }
            String trimmed = reason == null ? "" : reason.trim();
            if (trimmed.length() < 3 || trimmed.length() > 500) {
                throw ValidationException.of("reason", "Motivo deve ter entre 3 e 500 caracteres.");
            }
            Instant now = Instant.now(clock);
            TitleView updated = new TitleView(
                    current.id(),
                    current.tenantId(),
                    current.companyId(),
                    current.reference(),
                    current.direction(),
                    TitleStatus.CANCELLED,
                    current.description(),
                    current.counterpartyId(),
                    current.counterpartyCode(),
                    current.counterpartyName(),
                    current.counterpartyActive(),
                    current.categoryId(),
                    current.categoryCode(),
                    current.categoryName(),
                    current.categoryActive(),
                    current.amountMinor(),
                    current.currency(),
                    current.competenceDate(),
                    current.dueDate(),
                    false,
                    current.originKind(),
                    current.sourceReference(),
                    current.version() + 1,
                    current.createdAt(),
                    now,
                    current.createdBy(),
                    principal.actorId(),
                    current.confirmedAt(),
                    now,
                    trimmed,
                    current.companyDemo(),
                    current.settledAmountMinor(),
                    current.outstandingAmountMinor(),
                    SettlementStatus.NOT_APPLICABLE);
            if (titles.update(updated, current.version()) != 1) {
                throw new VersionConflictException();
            }
            titles.insertHistory(
                    UUID.randomUUID(),
                    updated,
                    HistoryAction.CANCELLED,
                    principal.actorId(),
                    clipName(principal.displayName()),
                    now,
                    trimmed,
                    changesJson(snapshot(current), snapshot(updated)));
            return updated;
        });
    }

    private TitleView withIdempotency(
            AuthorizedScope scope,
            ApplicationPrincipal principal,
            String operation,
            String key,
            String hash,
            java.util.function.Supplier<TitleView> action) {
        if (key == null || key.isBlank() || key.length() > 128) {
            throw ValidationException.of("Idempotency-Key", "Informe uma chave de idempotência de até 128 caracteres.");
        }
        access.requireWritable(principal, scope.companyId(), DemoPrincipalCatalog.PERMISSION_TITLES_WRITE);
        titles.advisoryLock(scope, principal.actorId(), operation, key.trim());
        var existing = titles.findIdempotency(scope, principal.actorId(), operation, key.trim());
        if (existing.isPresent()) {
            if (!existing.get().requestHash().equals(hash)) {
                throw new IdempotencyConflictException();
            }
            return readStored(existing.get().bodyJson());
        }
        TitleView created = action.get();
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

    private TitleView readStored(String bodyJson) {
        try {
            return mapper.readValue(bodyJson, TitleView.class);
        } catch (JsonProcessingException e) {
            throw new IllegalStateException("idempotency-body", e);
        }
    }

    private AuthorizedScope readable(ApplicationPrincipal principal, UUID companyId) {
        CompanyView company = access.requireReadable(principal, companyId);
        return new AuthorizedScope(company.tenantId(), company.id());
    }

    private boolean mutatingProtectedFields(TitleView current, TitleWriteCommand command) {
        String currentAmount = current.amountMinor() == null ? null : current.amountMinor().toPlainString();
        String nextAmount = command.amountMinor() == null || command.amountMinor().isBlank()
                ? null
                : command.amountMinor().trim();
        return !java.util.Objects.equals(currentAmount, nextAmount)
                || !java.util.Objects.equals(current.counterpartyId(), command.counterpartyId())
                || !java.util.Objects.equals(current.competenceDate(), command.competenceDate());
    }


    private record ParsedFields(
            String description, MoneyAmount amount, LocalDate competence, LocalDate due, String sourceReference, UUID counterpartyId, UUID categoryId) {}

    private ParsedFields parse(TitleWriteCommand command, boolean requireComplete) {
        Map<String, String> errors = new LinkedHashMap<>();
        String description = command.description() == null ? "" : command.description().trim();
        if (description.isEmpty() || description.length() > 200) {
            errors.put("description", "Descrição é obrigatória e deve ter até 200 caracteres.");
        }
        MoneyAmount amount = null;
        if (command.amountMinor() != null && !command.amountMinor().isBlank()) {
            try {
                amount = MoneyAmount.parseApi(command.amountMinor()).orElse(null);
            } catch (IllegalArgumentException ex) {
                errors.put("amountMinor", "Informe um valor inteiro positivo em centavos, somente dígitos.");
            }
        }
        if (command.currency() != null && !command.currency().isBlank() && !"BRL".equals(command.currency().trim())) {
            errors.put("currency", "Somente BRL é aceito nesta versão.");
        }
        String source = command.sourceReference() == null || command.sourceReference().isBlank()
                ? null
                : command.sourceReference().trim();
        if (source != null && source.length() > 100) {
            errors.put("sourceReference", "Referência informativa deve ter até 100 caracteres.");
        }
        if (command.reason() != null && command.reason().trim().length() > 500) {
            errors.put("reason", "Motivo deve ter até 500 caracteres.");
        }
        if (!errors.isEmpty()) {
            throw new ValidationException("Dados inválidos.", errors);
        }
        return new ParsedFields(
                description, amount, command.competenceDate(), command.dueDate(), source, command.counterpartyId(), command.categoryId());
    }

    private static void requireComplete(ParsedFields fields) {
        Map<String, String> errors = new LinkedHashMap<>();
        if (fields.counterpartyId == null) {
            errors.put("counterpartyId", "Contraparte é obrigatória para confirmar.");
        }
        if (fields.categoryId == null) {
            errors.put("categoryId", "Categoria é obrigatória para confirmar.");
        }
        if (fields.amount == null) {
            errors.put("amountMinor", "Valor é obrigatório para confirmar.");
        }
        if (fields.competence == null) {
            errors.put("competenceDate", "Competência é obrigatória para confirmar.");
        }
        if (fields.due == null) {
            errors.put("dueDate", "Vencimento é obrigatório para confirmar.");
        }
        if (!errors.isEmpty()) {
            throw new ValidationException("Preencha os campos obrigatórios.", errors);
        }
    }

    private record CatalogSnapshot(CounterpartyView counterparty, CategoryView category) {}

    private CatalogSnapshot resolveCatalogs(
            AuthorizedScope scope,
            TitleDirection direction,
            ParsedFields fields,
            boolean requireActive,
            TitleView current) {
        CounterpartyView counterparty = null;
        if (fields.counterpartyId != null) {
            counterparty = catalogs.lockCounterparty(scope, fields.counterpartyId)
                    .orElseThrow(() -> ValidationException.of("counterpartyId", "Contraparte não encontrada nesta empresa."));
            if (!counterparty.role().supports(direction)) {
                throw ValidationException.of("counterpartyId", "Contraparte incompatível com esta direção.");
            }
            boolean sameAsCurrent = current != null && fields.counterpartyId.equals(current.counterpartyId());
            if (requireActive && !counterparty.active() && !sameAsCurrent) {
                throw ValidationException.of("counterpartyId", "Contraparte inativa não pode ser selecionada.");
            }
            if (requireActive && !counterparty.active() && current == null) {
                throw ValidationException.of("counterpartyId", "Contraparte inativa não pode ser usada em confirmação.");
            }
        }
        CategoryView category = null;
        if (fields.categoryId != null) {
            category = catalogs.lockCategory(scope, fields.categoryId)
                    .orElseThrow(() -> ValidationException.of("categoryId", "Categoria não encontrada nesta empresa."));
            if (!category.direction().supports(direction)) {
                throw ValidationException.of("categoryId", "Categoria incompatível com esta direção.");
            }
            boolean sameAsCurrent = current != null && fields.categoryId.equals(current.categoryId());
            if (requireActive && !category.active() && !sameAsCurrent) {
                throw ValidationException.of("categoryId", "Categoria inativa não pode ser selecionada.");
            }
            if (requireActive && !category.active() && current == null) {
                throw ValidationException.of("categoryId", "Categoria inativa não pode ser usada em confirmação.");
            }
        }
        return new CatalogSnapshot(counterparty, category);
    }

    private Map<String, Object> snapshot(TitleView title) {
        if (title == null) {
            return Map.of();
        }
        Map<String, Object> map = new LinkedHashMap<>();
        map.put("description", title.description());
        map.put("status", title.status().name());
        map.put("amountMinor", title.amountMinor() == null ? null : title.amountMinor().toPlainString());
        map.put("competenceDate", title.competenceDate() == null ? null : title.competenceDate().toString());
        map.put("dueDate", title.dueDate() == null ? null : title.dueDate().toString());
        map.put("sourceReference", title.sourceReference());
        map.put(
                "counterparty",
                title.counterpartyId() == null
                        ? null
                        : Map.of(
                                "id", title.counterpartyId().toString(),
                                "code", String.valueOf(title.counterpartyCode()),
                                "name", String.valueOf(title.counterpartyName())));
        map.put(
                "category",
                title.categoryId() == null
                        ? null
                        : Map.of(
                                "id", title.categoryId().toString(),
                                "code", String.valueOf(title.categoryCode()),
                                "name", String.valueOf(title.categoryName())));
        return map;
    }

    private String changesJson(Map<String, Object> before, Map<String, Object> after) {
        List<Map<String, Object>> fields = new ArrayList<>();
        for (String key : List.of(
                "description", "status", "amountMinor", "competenceDate", "dueDate", "sourceReference", "counterparty", "category")) {
            Object left = before.get(key);
            Object right = after.get(key);
            if (java.util.Objects.equals(String.valueOf(left), String.valueOf(right))) {
                continue;
            }
            fields.add(Map.of("field", key, "before", left == null ? "" : left, "after", right == null ? "" : right));
        }
        return toJson(Map.of("fields", fields));
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
            digest.update(toJson(List.of(parts)).getBytes(StandardCharsets.UTF_8));
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
