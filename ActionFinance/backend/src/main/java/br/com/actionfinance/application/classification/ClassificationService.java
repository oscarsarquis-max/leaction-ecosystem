package br.com.actionfinance.application.classification;

import br.com.actionfinance.application.ApplicationPrincipal;
import br.com.actionfinance.application.finance.AuthorizedScope;
import br.com.actionfinance.application.finance.CompanyAccessService;
import br.com.actionfinance.application.finance.FinanceExceptions.IdempotencyConflictException;
import br.com.actionfinance.application.finance.FinanceExceptions.ValidationException;
import br.com.actionfinance.application.finance.FinanceExceptions.VersionConflictException;
import br.com.actionfinance.application.identity.FinancePermissions;
import br.com.actionfinance.infrastructure.persistence.JdbcTitleRepository;
import br.com.actionfinance.infrastructure.persistence.JdbcTitleRepository.IdempotencyRow;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.sql.Date;
import java.sql.Timestamp;
import java.time.Clock;
import java.time.Instant;
import java.time.LocalDate;
import java.util.ArrayList;
import java.util.HexFormat;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;

@Service
public class ClassificationService {

    private final JdbcTemplate jdbc;
    private final CompanyAccessService access;
    private final JdbcTitleRepository titles;
    private final ObjectMapper mapper;
    private final Clock clock;

    public ClassificationService(
            JdbcTemplate jdbc,
            CompanyAccessService access,
            JdbcTitleRepository titles,
            ObjectMapper mapper,
            Clock clock) {
        this.jdbc = jdbc;
        this.access = access;
        this.titles = titles;
        this.mapper = mapper;
        this.clock = clock;
    }

    public List<Map<String, Object>> initiatives(ApplicationPrincipal principal, UUID companyId) {
        AuthorizedScope scope = readCatalog(principal, companyId);
        return jdbc.query(
                """
                select id, code, name, active, version
                  from actionfinance.initiative
                 where tenant_id = ? and company_id = ?
                 order by name, code
                """,
                (rs, n) -> Map.of(
                        "id", rs.getObject("id", UUID.class),
                        "code", rs.getString("code"),
                        "name", rs.getString("name"),
                        "active", rs.getBoolean("active"),
                        "version", rs.getLong("version")),
                scope.tenantId(), scope.companyId());
    }

    @Transactional
    public Map<String, Object> createInitiative(
            ApplicationPrincipal principal, UUID companyId, String code, String name, String idempotencyKey) {
        AuthorizedScope scope = writeCatalog(principal, companyId);
        String stable = normalizeCode(code);
        String label = requireText(name, 2, 100, "name", "Informe o nome da iniciativa.");
        return replay(scope, principal, "catalogs.initiative", idempotencyKey, stable + "|" + label, () -> {
            UUID id = UUID.randomUUID();
            Instant now = Instant.now(clock);
            jdbc.update(
                    """
                    insert into actionfinance.initiative (
                        id, tenant_id, company_id, code, name, active, version, created_at, updated_at, created_by, updated_by
                    ) values (?,?,?,?,?,true,0,?,?,?,?)
                    """,
                    id, scope.tenantId(), scope.companyId(), stable, label, Timestamp.from(now), Timestamp.from(now),
                    principal.actorId(), principal.actorId());
            insertInitiativeHistory(scope, id, 0, label, true, "Cadastro da iniciativa.", now, principal.actorId());
            return Map.<String, Object>of("id", id, "code", stable, "name", label, "active", true, "version", 0);
        });
    }

    @Transactional
    public Map<String, Object> updateInitiative(
            ApplicationPrincipal principal, UUID companyId, UUID id, String name, Boolean active, long version, String reason, String idempotencyKey) {
        AuthorizedScope scope = writeCatalog(principal, companyId);
        String why = requireText(reason, 3, 300, "reason", "Informe o motivo da alteração.");
        return replay(scope, principal, "catalogs.initiative.update", idempotencyKey, id + "|" + version + "|" + name + "|" + active + "|" + why, () -> {
            List<Map<String, Object>> rows = jdbc.query(
                    """
                    select code, name, active, version from actionfinance.initiative
                     where tenant_id = ? and company_id = ? and id = ?
                     for update
                    """,
                    (rs, n) -> {
                        Map<String, Object> row = new LinkedHashMap<>();
                        row.put("code", rs.getString("code"));
                        row.put("name", rs.getString("name"));
                        row.put("active", rs.getBoolean("active"));
                        row.put("version", rs.getLong("version"));
                        return row;
                    },
                    scope.tenantId(), scope.companyId(), id);
            if (rows.isEmpty()) {
                throw new ValidationException("Iniciativa não encontrada nesta empresa.", Map.of("id", "Iniciativa não encontrada."));
            }
            Map<String, Object> current = rows.get(0);
            if ((long) current.get("version") != version) {
                throw new VersionConflictException("Esta iniciativa foi alterada. Revise antes de gravar.");
            }
            String nextName = name == null || name.isBlank() ? (String) current.get("name") : requireText(name, 2, 100, "name", "Informe o nome.");
            boolean nextActive = active == null ? (boolean) current.get("active") : active;
            Instant now = Instant.now(clock);
            int updated = jdbc.update(
                    """
                    update actionfinance.initiative
                       set name = ?, active = ?, version = version + 1, updated_at = ?, updated_by = ?
                     where tenant_id = ? and company_id = ? and id = ? and version = ?
                    """,
                    nextName, nextActive, Timestamp.from(now), principal.actorId(),
                    scope.tenantId(), scope.companyId(), id, version);
            if (updated != 1) {
                throw new VersionConflictException("Esta iniciativa foi alterada. Revise antes de gravar.");
            }
            insertInitiativeHistory(scope, id, version + 1, nextName, nextActive, why, now, principal.actorId());
            return Map.<String, Object>of("id", id, "code", current.get("code"), "name", nextName, "active", nextActive, "version", version + 1);
        });
    }

    @Transactional
    public Map<String, Object> mapApplication(
            ApplicationPrincipal principal, UUID companyId, String applicationCode, UUID initiativeId, String idempotencyKey) {
        AuthorizedScope scope = writeCatalog(principal, companyId);
        String code = requireText(applicationCode, 1, 80, "applicationCode", "Informe o código da aplicação.");
        return replay(scope, principal, "catalogs.initiative.map", idempotencyKey, code + "|" + initiativeId, () -> {
            requireInitiative(scope, initiativeId);
            jdbc.update(
                    """
                    insert into actionfinance.initiative_application_map (
                        id, tenant_id, company_id, application_code, initiative_id, created_at, created_by
                    ) values (?,?,?,?,?,?,?)
                    on conflict (tenant_id, company_id, application_code)
                    do update set initiative_id = excluded.initiative_id
                    """,
                    UUID.randomUUID(), scope.tenantId(), scope.companyId(), code, initiativeId,
                    Timestamp.from(Instant.now(clock)), principal.actorId());
            return Map.<String, Object>of("applicationCode", code, "initiativeId", initiativeId, "suggestionOnly", true);
        });
    }

    public List<Map<String, Object>> rules(ApplicationPrincipal principal, UUID companyId) {
        AuthorizedScope scope = readCatalog(principal, companyId);
        List<Map<String, Object>> rules = jdbc.query(
                """
                select id, name, active, version from actionfinance.allocation_rule
                 where tenant_id = ? and company_id = ?
                 order by name
                """,
                (rs, n) -> {
                    Map<String, Object> row = new LinkedHashMap<>();
                    row.put("id", rs.getObject("id", UUID.class));
                    row.put("name", rs.getString("name"));
                    row.put("active", rs.getBoolean("active"));
                    row.put("version", rs.getLong("version"));
                    return row;
                },
                scope.tenantId(), scope.companyId());
        for (Map<String, Object> rule : rules) {
            rule.put("versions", versions(scope, (UUID) rule.get("id")));
        }
        return rules;
    }

    @Transactional
    public Map<String, Object> createRule(
            ApplicationPrincipal principal,
            UUID companyId,
            String name,
            LocalDate validFrom,
            LocalDate validTo,
            List<AllocationMath.Share> shares,
            String idempotencyKey) {
        AuthorizedScope scope = writeCatalog(principal, companyId);
        String label = requireText(name, 2, 100, "name", "Informe o nome da regra.");
        if (validFrom == null) {
            throw ValidationException.of("validFrom", "Informe o início da vigência.");
        }
        assertComplete(shares);
        return replay(scope, principal, "catalogs.rule", idempotencyKey, label + "|" + validFrom + "|" + shares, () -> {
            UUID ruleId = UUID.randomUUID();
            Instant now = Instant.now(clock);
            jdbc.update(
                    """
                    insert into actionfinance.allocation_rule (
                        id, tenant_id, company_id, name, active, version, created_at, updated_at, created_by, updated_by
                    ) values (?,?,?,?,true,1,?,?,?,?)
                    """,
                    ruleId, scope.tenantId(), scope.companyId(), label, Timestamp.from(now), Timestamp.from(now),
                    principal.actorId(), principal.actorId());
            UUID versionId = insertRuleVersion(scope, ruleId, 1, validFrom, validTo, null, now, principal.actorId(), shares);
            return Map.<String, Object>of("id", ruleId, "name", label, "versionId", versionId, "versionNo", 1);
        });
    }

    @Transactional
    public Map<String, Object> addRuleVersion(
            ApplicationPrincipal principal,
            UUID companyId,
            UUID ruleId,
            LocalDate validFrom,
            LocalDate validTo,
            List<AllocationMath.Share> shares,
            String idempotencyKey) {
        AuthorizedScope scope = writeCatalog(principal, companyId);
        assertComplete(shares);
        if (validFrom == null) {
            throw ValidationException.of("validFrom", "Informe o início da vigência.");
        }
        return replay(scope, principal, "catalogs.rule.version", idempotencyKey, ruleId + "|" + validFrom + "|" + shares, () -> {
            Integer current = jdbc.queryForObject(
                    """
                    select version from actionfinance.allocation_rule
                     where tenant_id = ? and company_id = ? and id = ?
                     for update
                    """,
                    Integer.class, scope.tenantId(), scope.companyId(), ruleId);
            if (current == null) {
                throw new ValidationException("Regra não encontrada nesta empresa.", Map.of("ruleId", "Regra não encontrada."));
            }
            int next = current + 1;
            Instant now = Instant.now(clock);
            jdbc.update(
                    """
                    update actionfinance.allocation_rule
                       set version = ?, updated_at = ?, updated_by = ?
                     where tenant_id = ? and company_id = ? and id = ?
                    """,
                    next, Timestamp.from(now), principal.actorId(), scope.tenantId(), scope.companyId(), ruleId);
            UUID versionId = insertRuleVersion(scope, ruleId, next, validFrom, validTo, "Nova versão. O passado não foi recalculado.", now, principal.actorId(), shares);
            return Map.<String, Object>of("id", ruleId, "versionId", versionId, "versionNo", next, "recalculated", false);
        });
    }

    public Map<String, Object> queue(
            ApplicationPrincipal principal,
            UUID companyId,
            UUID accountId,
            LocalDate from,
            LocalDate to,
            String situation,
            String q,
            int page,
            int size) {
        AuthorizedScope scope = readAccounts(principal, companyId);
        List<Object> args = new ArrayList<>();
        StringBuilder where = baseWhere(scope, accountId, from, to, q, args);
        List<Map<String, Object>> all = loadLines(where, args);
        List<Map<String, Object>> filtered = new ArrayList<>();
        for (Map<String, Object> line : all) {
            if (situation == null || situation.isBlank() || situation.equals(line.get("situation"))) {
                filtered.add(line);
            }
        }
        int fromIndex = Math.max(0, page) * size;
        int toIndex = Math.min(filtered.size(), fromIndex + size);
        List<Map<String, Object>> slice = fromIndex >= filtered.size() ? List.of() : filtered.subList(fromIndex, toIndex);
        Map<String, Object> body = new LinkedHashMap<>();
        body.put("page", page);
        body.put("size", size);
        body.put("total", filtered.size());
        body.put("items", slice);
        body.put("coverage", coverageOf(all));
        return body;
    }

    public Map<String, Object> search(ApplicationPrincipal principal, UUID companyId, UUID accountId, String q) {
        AuthorizedScope scope = readAccounts(principal, companyId);
        String like = "%" + (q == null ? "" : q.trim().replace("%", "").replace("_", "")) + "%";
        List<Map<String, Object>> titlesFound = jdbc.query(
                """
                select id, reference, description, direction, status, amount_minor
                  from actionfinance.financial_title
                 where tenant_id = ? and company_id = ?
                   and (reference ilike ? or description ilike ?)
                 order by updated_at desc
                 limit 8
                """,
                (rs, n) -> Map.of(
                        "id", rs.getObject("id", UUID.class),
                        "reference", rs.getString("reference"),
                        "description", rs.getString("description"),
                        "direction", rs.getString("direction"),
                        "status", rs.getString("status"),
                        "amountMinor", rs.getObject("amount_minor") == null ? 0 : rs.getLong("amount_minor")),
                scope.tenantId(), scope.companyId(), like, like);
        List<Map<String, Object>> movements = accountId == null ? List.of() : jdbc.query(
                """
                select id, effective_date, description, signed_amount_minor, kind
                  from actionfinance.cash_movement
                 where tenant_id = ? and company_id = ? and account_id = ?
                   and description ilike ?
                 order by effective_date desc
                 limit 8
                """,
                (rs, n) -> Map.of(
                        "id", rs.getObject("id", UUID.class),
                        "effectiveDate", rs.getDate("effective_date").toLocalDate().toString(),
                        "description", rs.getString("description"),
                        "signedMinor", rs.getLong("signed_amount_minor"),
                        "kind", rs.getString("kind")),
                scope.tenantId(), scope.companyId(), accountId, like);
        return Map.of("titles", titlesFound, "movements", movements);
    }

    public Map<String, Object> detail(ApplicationPrincipal principal, UUID companyId, UUID lineId) {
        AuthorizedScope scope = readAccounts(principal, companyId);
        List<Map<String, Object>> lines = loadLines(new StringBuilder(" where l.tenant_id = ? and l.company_id = ? and l.id = ? "), new ArrayList<>(List.of(scope.tenantId(), scope.companyId(), lineId)));
        if (lines.isEmpty()) {
            throw new ValidationException("Movimento não encontrado nesta empresa.", Map.of("lineId", "Movimento não encontrado."));
        }
        Map<String, Object> line = new LinkedHashMap<>(lines.get(0));
        line.put("shares", shares(scope, lineId));
        line.put("references", references(scope, lineId));
        line.put("book", book(scope, lineId));
        line.put("history", history(scope, lineId));
        line.put("suggestions", suggestions(scope, line));
        return line;
    }

    @Transactional
    public Map<String, Object> classify(ApplicationPrincipal principal, UUID companyId, ClassifyCommand command, String idempotencyKey) {
        AuthorizedScope scope = writeAccounts(principal, companyId);
        return replay(scope, principal, "classification.apply", idempotencyKey, json(command), () -> applyClassify(scope, principal, command));
    }

    @Transactional
    public Map<String, Object> reference(ApplicationPrincipal principal, UUID companyId, ReferenceCommand command, String idempotencyKey) {
        AuthorizedScope scope = writeAccounts(principal, companyId);
        return replay(scope, principal, "classification.reference", idempotencyKey, json(command), () -> applyReference(scope, principal, command));
    }

    @Transactional
    public Map<String, Object> book(ApplicationPrincipal principal, UUID companyId, BookCommand command, String idempotencyKey) {
        AuthorizedScope scope = writeAccounts(principal, companyId);
        return replay(scope, principal, "classification.book", idempotencyKey, json(command), () -> applyBook(scope, principal, command));
    }

    @Transactional
    public Map<String, Object> undo(ApplicationPrincipal principal, UUID companyId, UndoCommand command, String idempotencyKey) {
        AuthorizedScope scope = writeAccounts(principal, companyId);
        String why = requireText(command.reason(), 3, 300, "reason", "Informe o motivo para desfazer.");
        return replay(scope, principal, "classification.undo", idempotencyKey, json(command), () -> applyUndo(scope, principal, command, why));
    }

    @Transactional
    public Map<String, Object> note(ApplicationPrincipal principal, UUID companyId, UUID occurrenceId, UUID categoryId, String note, String idempotencyKey) {
        AuthorizedScope scope = writeAccounts(principal, companyId);
        return replay(scope, principal, "classification.note", idempotencyKey, occurrenceId + "|" + categoryId + "|" + note, () -> {
            Integer linked = jdbc.queryForObject(
                    """
                    select count(*) from actionfinance.statement_occurrence
                     where tenant_id = ? and company_id = ? and id = ? and line_id is null
                    """,
                    Integer.class, scope.tenantId(), scope.companyId(), occurrenceId);
            if (linked == null || linked == 0) {
                throw new ValidationException(
                        "Só uma ocorrência sem evento identificável recebe anotação documental.",
                        Map.of("occurrenceId", "Esta ocorrência não é só documental."));
            }
            UUID id = UUID.randomUUID();
            jdbc.update(
                    """
                    insert into actionfinance.statement_occurrence_note (
                        id, tenant_id, company_id, occurrence_id, category_id, note, version, updated_at, updated_by
                    ) values (?,?,?,?,?,?,0,?,?)
                    on conflict (tenant_id, company_id, occurrence_id)
                    do update set category_id = excluded.category_id, note = excluded.note,
                                  version = actionfinance.statement_occurrence_note.version + 1,
                                  updated_at = excluded.updated_at, updated_by = excluded.updated_by
                    """,
                    id, scope.tenantId(), scope.companyId(), occurrenceId, categoryId, note,
                    Timestamp.from(Instant.now(clock)), principal.actorId());
            return Map.<String, Object>of("occurrenceId", occurrenceId, "documentary", true, "inFinancialTotal", false);
        });
    }

    public List<Map<String, Object>> labels(AuthorizedScope scope, List<UUID> lineIds) {
        if (lineIds.isEmpty()) {
            return List.of();
        }
        String marks = String.join(",", lineIds.stream().map(id -> "?").toList());
        List<Object> args = new ArrayList<>();
        args.add(scope.tenantId());
        args.add(scope.companyId());
        args.addAll(lineIds);
        return jdbc.query(
                """
                select l.id,
                       coalesce(c.name, 'Sem categoria') as category_name,
                       case
                         when d.assignment = 'SINGLE' then i.name
                         when d.assignment = 'ALLOCATED' then 'Rateio'
                         else 'Não atribuída'
                       end as initiative_name,
                       l.import_status, l.balance_effect, l.availability, l.net_absent, l.currency_assumed, l.direction,
                       l.net_minor,
                       coalesce((select abs(sum(a.movement_sign * a.allocated_minor)) from actionfinance.statement_book_allocation a
                          where a.line_id = l.id and a.status = 'ACTIVE'), 0) as book_minor,
                       coalesce((select bool_or(
                            (select coalesce(sum(a2.allocated_minor), 0) from actionfinance.statement_book_allocation a2
                              where a2.movement_id = a.movement_id and a2.status = 'ACTIVE') < abs(m.signed_amount_minor))
                          from actionfinance.statement_book_allocation a
                          join actionfinance.cash_movement m on m.id = a.movement_id
                         where a.line_id = l.id and a.status = 'ACTIVE'), false) as book_residual,
                       coalesce((select count(*) from actionfinance.statement_reference_link r
                          where r.line_id = l.id and r.status = 'ACTIVE'), 0) as reference_count
                  from actionfinance.statement_line l
                  left join actionfinance.statement_decision d
                    on d.tenant_id = l.tenant_id and d.company_id = l.company_id and d.line_id = l.id
                  left join actionfinance.financial_category c
                    on c.tenant_id = d.tenant_id and c.company_id = d.company_id and c.id = d.category_id
                  left join actionfinance.initiative i
                    on i.tenant_id = d.tenant_id and i.company_id = d.company_id and i.id = d.initiative_id
                 where l.tenant_id = ? and l.company_id = ? and l.id in (%s)
                """.formatted(marks),
                (rs, n) -> {
                    boolean eligible = "ACTIVE".equals(rs.getString("import_status"))
                            && "AFFECTS".equals(rs.getString("balance_effect"))
                            && "RELEASED".equals(rs.getString("availability"))
                            && !rs.getBoolean("net_absent")
                            && !rs.getBoolean("currency_assumed")
                            && ("IN".equals(rs.getString("direction")) || "OUT".equals(rs.getString("direction")));
                    long net = rs.getObject("net_minor") == null ? 0 : rs.getLong("net_minor");
                    Map<String, Object> row = new LinkedHashMap<>();
                    row.put("id", rs.getObject("id", UUID.class));
                    row.put("category", rs.getString("category_name"));
                    row.put("initiative", rs.getString("initiative_name"));
                    row.put("situation", situation(eligible, net, rs.getLong("book_minor"), rs.getLong("reference_count"), rs.getBoolean("book_residual")));
                    return row;
                },
                args.toArray());
    }

    private Map<String, Object> applyClassify(AuthorizedScope scope, ApplicationPrincipal principal, ClassifyCommand command) {
        if (command.lineIds() == null || command.lineIds().isEmpty()) {
            throw ValidationException.of("lineIds", "Selecione ao menos um movimento.");
        }
        List<UUID> ordered = command.lineIds().stream().distinct().sorted().toList();
        List<Map<String, Object>> skipped = new ArrayList<>();
        List<Map<String, Object>> conflicts = new ArrayList<>();
        List<LockedLine> applicable = new ArrayList<>();
        for (UUID lineId : ordered) {
            LockedLine line = lockLine(scope, lineId);
            if (line == null) {
                skipped.add(Map.of("lineId", lineId, "reason", "Movimento não encontrado nesta empresa."));
                continue;
            }
            long actual = decisionVersion(scope, lineId);
            Long expected = command.versions() == null ? null : command.versions().get(lineId.toString());
            if (expected == null || expected != actual) {
                conflicts.add(Map.of("lineId", lineId, "version", actual));
                continue;
            }
            String problem = classifyProblem(scope, line, command);
            if (problem != null) {
                skipped.add(Map.of("lineId", lineId, "reason", problem));
                continue;
            }
            applicable.add(line);
        }
        Map<String, Object> preview = new LinkedHashMap<>();
        preview.put("preview", command.preview());
        preview.put("selected", ordered.size());
        preview.put("applicable", applicable.size());
        preview.put("skipped", skipped);
        preview.put("conflicts", conflicts);
        if (!conflicts.isEmpty()) {
            if (command.preview()) {
                return preview;
            }
            throw new VersionConflictException(
                    "Há itens alterados por outra sessão. Nada foi gravado.",
                    Map.of("conflicts", conflicts.toString()));
        }
        if (command.preview()) {
            preview.put("effect", "A confirmação grava só os itens válidos, na mesma transação.");
            return preview;
        }
        if (applicable.isEmpty()) {
            throw new ValidationException("Nenhum item selecionado pode receber esta classificação.", Map.of("lineIds", skipped.toString()));
        }
        Instant now = Instant.now(clock);
        for (LockedLine line : applicable) {
            saveDecision(scope, principal, line, command, now);
        }
        preview.put("saved", applicable.size());
        return preview;
    }

    private void saveDecision(AuthorizedScope scope, ApplicationPrincipal principal, LockedLine line, ClassifyCommand command, Instant now) {
        long version = decisionVersion(scope, line.id()) + 1;
        UUID decisionId = decisionId(scope, line.id());
        boolean fresh = decisionId == null;
        if (fresh) {
            decisionId = UUID.randomUUID();
        }
        String previous = decisionState(scope, line.id());
        String assignment = command.assignment();
        UUID initiativeId = "SINGLE".equals(assignment) ? command.initiativeId() : null;
        UUID ruleVersionId = "ALLOCATED".equals(assignment) && command.ruleVersionId() != null ? command.ruleVersionId() : null;
        if ("ALLOCATED".equals(assignment) && ruleVersionId == null && (command.shares() == null || command.shares().isEmpty())) {
            assignment = "UNASSIGNED";
        }
        Long basis = monetaryBasis(line);
        String dateBasis = line.effectiveOn() != null ? "APPROVAL" : command.manualOn() != null ? "MANUAL" : "ABSENT";
        UUID categoryId = command.clearCategory() ? null : command.categoryId() != null ? command.categoryId() : currentCategory(scope, line.id());
        if (fresh) {
            jdbc.update(
                    """
                    insert into actionfinance.statement_decision (
                        id, tenant_id, company_id, line_id, version, category_id, assignment, initiative_id, rule_version_id,
                        basis_minor, date_basis, manual_on, review_required, updated_at, updated_by
                    ) values (?,?,?,?,?,?,?,?,?,?,?,?,false,?,?)
                    """,
                    decisionId, scope.tenantId(), scope.companyId(), line.id(), version, categoryId, assignment, initiativeId, ruleVersionId,
                    basis, dateBasis, command.manualOn() == null ? null : Date.valueOf(command.manualOn()),
                    Timestamp.from(now), principal.actorId());
        } else {
            jdbc.update(
                    """
                    update actionfinance.statement_decision
                       set version = ?, category_id = ?, assignment = ?, initiative_id = ?, rule_version_id = ?,
                           basis_minor = ?, date_basis = ?, manual_on = ?, review_required = false, updated_at = ?, updated_by = ?
                     where tenant_id = ? and company_id = ? and line_id = ?
                    """,
                    version, categoryId, assignment, initiativeId, ruleVersionId, basis, dateBasis,
                    command.manualOn() == null ? null : Date.valueOf(command.manualOn()),
                    Timestamp.from(now), principal.actorId(), scope.tenantId(), scope.companyId(), line.id());
            jdbc.update(
                    "delete from actionfinance.statement_decision_share where tenant_id = ? and company_id = ? and decision_id = ?",
                    scope.tenantId(), scope.companyId(), decisionId);
        }
        if (basis != null && basis > 0) {
            List<AllocationMath.Portion> portions = portionsFor(scope, assignment, initiativeId, ruleVersionId, command.shares(), basis);
            for (AllocationMath.Portion portion : portions) {
                jdbc.update(
                        """
                        insert into actionfinance.statement_decision_share (
                            id, tenant_id, company_id, decision_id, initiative_id, amount_minor, basis_points, criterion
                        ) values (?,?,?,?,?,?,?,?)
                        """,
                        UUID.randomUUID(), scope.tenantId(), scope.companyId(), decisionId,
                        portion.initiativeId() == null ? null : UUID.fromString(portion.initiativeId()),
                        portion.amountMinor(), portion.basisPoints() == 0 ? null : portion.basisPoints(),
                        portion.initiativeId() == null ? "Não atribuída" : AllocationMath.CRITERION);
            }
        }
        jdbc.update(
                """
                insert into actionfinance.statement_decision_history (
                    id, tenant_id, company_id, decision_id, version, reason, previous_state, next_state, changed_at, changed_by
                ) values (?,?,?,?,?,?,?::jsonb,?::jsonb,?,?)
                """,
                UUID.randomUUID(), scope.tenantId(), scope.companyId(), decisionId, version,
                command.reason() == null || command.reason().isBlank() ? "Classificação do operador." : command.reason(),
                previous, decisionState(scope, line.id()), Timestamp.from(now), principal.actorId());
    }

    private List<AllocationMath.Portion> portionsFor(
            AuthorizedScope scope, String assignment, UUID initiativeId, UUID ruleVersionId, List<AllocationMath.Share> manual, long basis) {
        if ("SINGLE".equals(assignment) && initiativeId != null) {
            String code = jdbc.queryForObject(
                    "select code from actionfinance.initiative where tenant_id = ? and company_id = ? and id = ?",
                    String.class, scope.tenantId(), scope.companyId(), initiativeId);
            return AllocationMath.split(basis, List.of(new AllocationMath.Share(initiativeId.toString(), code, 10000)));
        }
        if (ruleVersionId != null) {
            return AllocationMath.split(basis, ruleShares(scope, ruleVersionId));
        }
        if (manual != null && !manual.isEmpty()) {
            return AllocationMath.split(basis, manual);
        }
        return List.of(new AllocationMath.Portion(null, "", 10000, basis, false));
    }

    private Map<String, Object> applyReference(AuthorizedScope scope, ApplicationPrincipal principal, ReferenceCommand command) {
        LockedLine line = lockLine(scope, command.lineId());
        if (line == null) {
            throw new ValidationException("Movimento não encontrado nesta empresa.", Map.of("lineId", "Movimento não encontrado."));
        }
        if (command.allocatedMinor() <= 0) {
            throw ValidationException.of("allocatedMinor", "Informe um valor maior que zero.");
        }
        long lineSide = basisAmount(line, command.comparedBasis());
        if (lineSide < 0 && !"CONFIRMED_PAID".equals(command.comparedBasis())) {
            throw new ValidationException("Esta base não está disponível no extrato.", Map.of("comparedBasis", "Base ausente no extrato."));
        }
        if (lineSide >= 0 && command.allocatedMinor() > lineSide) {
            throw new ValidationException("O vínculo passa do valor desta base no extrato.", Map.of("allocatedMinor", "Acima do extrato."));
        }
        lockTarget(scope, command);
        long usedOnLine = activeReferenceSum(scope, command.lineId(), command.comparedBasis());
        if (lineSide >= 0 && usedOnLine + command.allocatedMinor() > lineSide) {
            throw new ValidationException("Esta base do extrato já está ocupada por outro vínculo.", Map.of("allocatedMinor", "Limite da linha."));
        }
        long targetLimit = targetLimit(scope, command);
        long usedOnTarget = activeTargetSum(scope, command);
        if (usedOnTarget + command.allocatedMinor() > targetLimit) {
            throw new ValidationException("Este registro já não tem saldo bastante nesta base.", Map.of("allocatedMinor", "Limite da outra ponta."));
        }
        UUID id = UUID.randomUUID();
        Instant now = Instant.now(clock);
        jdbc.update(
                """
                insert into actionfinance.statement_reference_link (
                    id, tenant_id, company_id, line_id, target_kind, title_id, pay_receipt_id, compared_basis,
                    allocated_minor, status, version, updated_at, updated_by
                ) values (?,?,?,?,?,?,?,?,?,'ACTIVE',0,?,?)
                """,
                id, scope.tenantId(), scope.companyId(), command.lineId(), command.targetKind(),
                command.titleId(), command.payReceiptId(), command.comparedBasis(), command.allocatedMinor(),
                Timestamp.from(now), principal.actorId());
        linkHistory(scope, command.lineId(), "REFERENCE", id, "CONFIRMED", "Referência confirmada pelo operador. Não baixa título nem concilia o livro.", command.allocatedMinor(), now, principal.actorId());
        Map<String, Object> body = new LinkedHashMap<>();
        body.put("id", id);
        body.put("effect", "REFERENCE");
        body.put("bookReconciled", false);
        body.put("titleStatusUnchanged", true);
        body.put("differenceMinor", lineSide < 0 ? null : lineSide - (usedOnLine + command.allocatedMinor()));
        return body;
    }

    private Map<String, Object> applyBook(AuthorizedScope scope, ApplicationPrincipal principal, BookCommand command) {
        LockedLine line = lockLine(scope, command.lineId());
        if (line == null) {
            throw new ValidationException("Movimento não encontrado nesta empresa.", Map.of("lineId", "Movimento não encontrado."));
        }
        String block = bookBlock(line);
        if (block != null) {
            throw new ValidationException(block, Map.of("lineId", block));
        }
        if (command.components() == null || command.components().isEmpty()) {
            throw ValidationException.of("components", "Escolha ao menos um movimento do livro.");
        }
        long signed = 0;
        List<String> equation = new ArrayList<>();
        for (BookComponent component : command.components()) {
            MovementRow movement = lockMovement(scope, line.accountId(), component.movementId());
            if (movement == null) {
                throw new ValidationException("Movimento do livro não encontrado nesta conta.", Map.of("movementId", "Conta ou empresa incompatível."));
            }
            if (movement.reversed()) {
                throw new ValidationException("Este movimento já foi estornado.", Map.of("movementId", "Baixa estornada."));
            }
            long abs = Math.abs(movement.signedMinor());
            long used = activeBookSum(scope, movement.id());
            if (component.allocatedMinor() <= 0 || used + component.allocatedMinor() > abs) {
                throw new ValidationException("A alocação passa do valor disponível deste movimento.", Map.of("allocatedMinor", "Limite do movimento."));
            }
            int sign = movement.signedMinor() < 0 ? -1 : 1;
            signed += sign * component.allocatedMinor();
            equation.add((sign < 0 ? "− " : "+ ") + component.allocatedMinor());
        }
        boolean componentsClosed = true;
        for (BookComponent component : command.components()) {
            MovementRow movement = lockMovement(scope, line.accountId(), component.movementId());
            long used = activeBookSum(scope, movement.id()) + component.allocatedMinor();
            if (used != Math.abs(movement.signedMinor())) {
                componentsClosed = false;
            }
        }
        long net = line.netMinor();
        int lineSign = "OUT".equals(line.direction()) ? -1 : 1;
        if (command.components().size() > 1 && signed != lineSign * net && !command.allowPartial()) {
            throw new ValidationException(
                    "A equação do grupo não representa o líquido do extrato. Nada foi gravado.",
                    Map.of("equation", String.join(" ", equation) + " = " + signed + "; líquido " + (lineSign * net)));
        }
        long alreadySigned = activeBookSigned(scope, line.id());
        long next = alreadySigned + signed;
        long target = lineSign * net;
        if (next != 0 && Long.signum(next) != Long.signum(target)) {
            throw new ValidationException("O sinal do grupo não combina com a direção do extrato.", Map.of("components", "Direção incompatível."));
        }
        if (Math.abs(next) > Math.abs(target)) {
            throw new ValidationException("A conciliação passa do líquido deste evento.", Map.of("allocatedMinor", "Limite do extrato."));
        }
        Instant now = Instant.now(clock);
        UUID groupId = command.components().size() > 1 ? UUID.randomUUID() : null;
        if (groupId != null) {
            jdbc.update(
                    """
                    insert into actionfinance.statement_book_group (
                        id, tenant_id, company_id, line_id, equation, status, version, updated_at, updated_by
                    ) values (?,?,?,?,?,'ACTIVE',0,?,?)
                    """,
                    groupId, scope.tenantId(), scope.companyId(), line.id(), String.join(" ", equation) + " = " + signed,
                    Timestamp.from(now), principal.actorId());
        }
        List<UUID> ids = new ArrayList<>();
        for (BookComponent component : command.components()) {
            MovementRow movement = lockMovement(scope, line.accountId(), component.movementId());
            UUID id = UUID.randomUUID();
            ids.add(id);
            int sign = movement.signedMinor() < 0 ? -1 : 1;
            jdbc.update(
                    """
                    insert into actionfinance.statement_book_allocation (
                        id, tenant_id, company_id, line_id, group_id, movement_id, allocated_minor, movement_sign,
                        status, version, updated_at, updated_by
                    ) values (?,?,?,?,?,?,?,?,'ACTIVE',0,?,?)
                    """,
                    id, scope.tenantId(), scope.companyId(), line.id(), groupId, component.movementId(),
                    component.allocatedMinor(), sign, Timestamp.from(now), principal.actorId());
            linkHistory(scope, line.id(), "BOOK", id, "CONFIRMED", "Conciliação com o livro. Não cria movimento.", component.allocatedMinor(), now, principal.actorId());
        }
        Map<String, Object> body = new LinkedHashMap<>();
        body.put("ids", ids);
        body.put("groupId", groupId);
        body.put("effect", "BOOK");
        body.put("equation", String.join(" ", equation));
        body.put("fullyReconciled", next == target && componentsClosed);
        return body;
    }

    private Map<String, Object> applyUndo(AuthorizedScope scope, ApplicationPrincipal principal, UndoCommand command, String reason) {
        Instant now = Instant.now(clock);
        String table = "REFERENCE".equals(command.kind()) ? "statement_reference_link" : "statement_book_allocation";
        int updated = jdbc.update(
                """
                update actionfinance.%s
                   set status = 'UNDONE', version = version + 1, updated_at = ?, updated_by = ?
                 where tenant_id = ? and company_id = ? and id = ? and status = 'ACTIVE' and version = ?
                """.formatted(table),
                Timestamp.from(now), principal.actorId(), scope.tenantId(), scope.companyId(), command.id(), command.version());
        if (updated != 1) {
            throw new VersionConflictException("Este vínculo mudou ou já não está ativo. Nada foi desfeito.");
        }
        UUID lineId = jdbc.queryForObject(
                "select line_id from actionfinance." + table + " where id = ?",
                UUID.class, command.id());
        linkHistory(scope, lineId, command.kind(), command.id(), "UNDONE", reason, null, now, principal.actorId());
        return Map.of("id", command.id(), "status", "UNDONE", "occurrencePreserved", true, "settlementPreserved", true);
    }

    private String classifyProblem(AuthorizedScope scope, LockedLine line, ClassifyCommand command) {
        if (command.categoryId() != null && !categoryFits(scope, command.categoryId(), line.direction())) {
            return "A categoria não combina com a direção deste movimento.";
        }
        if ("SINGLE".equals(command.assignment()) && command.initiativeId() != null) {
            try {
                requireInitiative(scope, command.initiativeId());
            } catch (ValidationException exception) {
                return exception.getMessage();
            }
        }
        if (command.ruleVersionId() != null) {
            if (monetaryBasis(line) == null) {
                return "Não há líquido conhecido para ratear.";
            }
            LocalDate when = line.effectiveOn() != null ? line.effectiveOn() : command.manualOn();
            if (when == null) {
                return "Sem data confiável não escolho uma regra vigente. Informe a data desta decisão.";
            }
            if (!ruleCovers(scope, command.ruleVersionId(), when)) {
                return "A regra não vale na data deste movimento.";
            }
        }
        return null;
    }

    private boolean categoryFits(AuthorizedScope scope, UUID categoryId, String direction) {
        List<String> rows = jdbc.query(
                """
                select direction from actionfinance.financial_category
                 where tenant_id = ? and company_id = ? and id = ? and active
                """,
                (rs, n) -> rs.getString("direction"), scope.tenantId(), scope.companyId(), categoryId);
        if (rows.isEmpty()) {
            return false;
        }
        String category = rows.get(0);
        if ("NONE".equals(direction)) {
            return false;
        }
        if ("BOTH".equals(category)) {
            return true;
        }
        return ("IN".equals(direction) && "RECEIVABLE".equals(category)) || ("OUT".equals(direction) && "PAYABLE".equals(category));
    }

    private boolean ruleCovers(AuthorizedScope scope, UUID versionId, LocalDate when) {
        Integer count = jdbc.queryForObject(
                """
                select count(*) from actionfinance.allocation_rule_version
                 where tenant_id = ? and company_id = ? and id = ?
                   and valid_from <= ? and (valid_to is null or valid_to >= ?)
                """,
                Integer.class, scope.tenantId(), scope.companyId(), versionId, Date.valueOf(when), Date.valueOf(when));
        return count != null && count > 0;
    }

    private List<AllocationMath.Share> ruleShares(AuthorizedScope scope, UUID versionId) {
        return jdbc.query(
                """
                select i.id, i.code, s.basis_points
                  from actionfinance.allocation_rule_share s
                  join actionfinance.initiative i
                    on i.tenant_id = s.tenant_id and i.company_id = s.company_id and i.id = s.initiative_id
                 where s.tenant_id = ? and s.company_id = ? and s.version_id = ?
                """,
                (rs, n) -> new AllocationMath.Share(rs.getObject("id", UUID.class).toString(), rs.getString("code"), rs.getInt("basis_points")),
                scope.tenantId(), scope.companyId(), versionId);
    }

    private StringBuilder baseWhere(AuthorizedScope scope, UUID accountId, LocalDate from, LocalDate to, String q, List<Object> args) {
        StringBuilder where = new StringBuilder(" where l.tenant_id = ? and l.company_id = ? ");
        args.add(scope.tenantId());
        args.add(scope.companyId());
        if (accountId != null) {
            where.append(" and l.account_id = ? ");
            args.add(accountId);
        }
        if (from != null) {
            where.append(" and l.effective_on >= ? ");
            args.add(Date.valueOf(from));
        }
        if (to != null) {
            where.append(" and l.effective_on <= ? ");
            args.add(Date.valueOf(to));
        }
        if (q != null && !q.isBlank()) {
            where.append(" and (coalesce(l.description,'') ilike ? or coalesce(l.external_reference,'') ilike ?) ");
            String like = "%" + q.trim().replace("%", "").replace("_", "") + "%";
            args.add(like);
            args.add(like);
        }
        return where;
    }

    private List<Map<String, Object>> loadLines(StringBuilder where, List<Object> args) {
        return jdbc.query(
                """
                select l.id, l.account_id, l.description, l.external_reference, l.effective_on, l.direction, l.event_kind,
                       l.gross_minor, l.gross_absent, l.fee_minor, l.fee_absent, l.net_minor, l.net_absent,
                       l.balance_effect, l.availability, l.import_status, l.currency_assumed, l.source_id,
                       d.version as decision_version, d.assignment, d.review_required, c.name as category_name,
                       i.name as initiative_name,
                       coalesce((select abs(sum(a.movement_sign * a.allocated_minor)) from actionfinance.statement_book_allocation a
                          where a.line_id = l.id and a.status = 'ACTIVE'), 0) as book_minor,
                       coalesce((select bool_or(
                            (select coalesce(sum(a2.allocated_minor), 0) from actionfinance.statement_book_allocation a2
                              where a2.movement_id = a.movement_id and a2.status = 'ACTIVE') < abs(m.signed_amount_minor))
                          from actionfinance.statement_book_allocation a
                          join actionfinance.cash_movement m on m.id = a.movement_id
                         where a.line_id = l.id and a.status = 'ACTIVE'), false) as book_residual,
                       coalesce((select count(*) from actionfinance.statement_reference_link r
                          where r.line_id = l.id and r.status = 'ACTIVE'), 0) as reference_count
                  from actionfinance.statement_line l
                  left join actionfinance.statement_decision d
                    on d.tenant_id = l.tenant_id and d.company_id = l.company_id and d.line_id = l.id
                  left join actionfinance.financial_category c
                    on c.tenant_id = d.tenant_id and c.company_id = d.company_id and c.id = d.category_id
                  left join actionfinance.initiative i
                    on i.tenant_id = d.tenant_id and i.company_id = d.company_id and i.id = d.initiative_id
                """ + where + " order by l.effective_on desc nulls last, l.id desc",
                (rs, n) -> mapQueue(rs),
                args.toArray());
    }

    private Map<String, Object> mapQueue(java.sql.ResultSet rs) throws java.sql.SQLException {
        Map<String, Object> row = new LinkedHashMap<>();
        boolean eligible = eligible(rs);
        long net = rs.getObject("net_minor") == null ? 0 : rs.getLong("net_minor");
        long book = rs.getLong("book_minor");
        long references = rs.getLong("reference_count");
        String situation = situation(eligible, net, book, references, rs.getBoolean("book_residual"));
        row.put("lineId", rs.getObject("id", UUID.class));
        row.put("accountId", rs.getObject("account_id", UUID.class));
        row.put("description", rs.getString("description"));
        row.put("externalReference", rs.getString("external_reference"));
        row.put("effectiveOn", rs.getObject("effective_on", LocalDate.class));
        row.put("dateLabel", rs.getObject("effective_on") == null ? "Sem data confiável" : "Data de aprovação");
        row.put("direction", rs.getString("direction"));
        row.put("eventKind", rs.getString("event_kind"));
        row.put("grossMinor", rs.getObject("gross_minor") == null ? null : rs.getLong("gross_minor"));
        row.put("feeMinor", rs.getObject("fee_minor") == null ? null : rs.getLong("fee_minor"));
        row.put("netMinor", rs.getObject("net_minor") == null ? null : rs.getLong("net_minor"));
        row.put("netAbsent", rs.getBoolean("net_absent"));
        row.put("category", rs.getString("category_name") == null ? "Sem categoria" : rs.getString("category_name"));
        row.put("initiative", rs.getString("initiative_name") == null ? "Não atribuída" : rs.getString("initiative_name"));
        row.put("assignment", rs.getString("assignment"));
        row.put("reviewRequired", rs.getBoolean("review_required"));
        row.put("version", rs.getObject("decision_version") == null ? 0 : rs.getLong("decision_version"));
        row.put("eligible", eligible);
        row.put("situation", situation);
        row.put("bookMinor", book);
        row.put("referenceCount", references);
        row.put("sourceId", rs.getString("source_id"));
        return row;
    }

    private static boolean eligible(java.sql.ResultSet rs) throws java.sql.SQLException {
        return "ACTIVE".equals(rs.getString("import_status"))
                && "AFFECTS".equals(rs.getString("balance_effect"))
                && "RELEASED".equals(rs.getString("availability"))
                && !rs.getBoolean("net_absent")
                && !rs.getBoolean("currency_assumed")
                && ("IN".equals(rs.getString("direction")) || "OUT".equals(rs.getString("direction")));
    }

    private static String situation(boolean eligible, long net, long book, long references, boolean residual) {
        if (!eligible) {
            return "FORA";
        }
        if (net > 0 && book == net && !residual) {
            return "CONCILIADO";
        }
        if (book > 0 && book < net) {
            return "PARCIAL";
        }
        if (book > 0) {
            return "DIVERGENCIA";
        }
        if (references > 0) {
            return "REFERENCIA";
        }
        return "SEM_CORRESPONDENCIA";
    }

    private Map<String, Object> coverageOf(List<Map<String, Object>> lines) {
        long inBase = 0;
        long outBase = 0;
        long inBook = 0;
        long outBook = 0;
        long eligible = 0;
        long classified = 0;
        long documentary = 0;
        for (Map<String, Object> line : lines) {
            if (!Boolean.TRUE.equals(line.get("eligible"))) {
                documentary++;
                continue;
            }
            eligible++;
            long net = line.get("netMinor") == null ? 0 : ((Number) line.get("netMinor")).longValue();
            long book = ((Number) line.get("bookMinor")).longValue();
            if ("IN".equals(line.get("direction"))) {
                inBase += net;
                inBook += Math.min(book, net);
            } else if ("OUT".equals(line.get("direction"))) {
                outBase += net;
                outBook += Math.min(book, net);
            }
            if (line.get("category") != null && !"Sem categoria".equals(line.get("category"))) {
                classified++;
            }
        }
        Map<String, Object> coverage = new LinkedHashMap<>();
        coverage.put("eligibleCount", eligible);
        coverage.put("documentaryCount", documentary);
        coverage.put("classifiedCount", classified);
        coverage.put("inBaseMinor", inBase);
        coverage.put("outBaseMinor", outBase);
        coverage.put("inBookMinor", inBook);
        coverage.put("outBookMinor", outBook);
        coverage.put("inPendingMinor", inBase - inBook);
        coverage.put("outPendingMinor", outBase - outBook);
        coverage.put("note", "O valor conciliado é só a parcela ativa no livro. Referência comercial não entra nesta soma.");
        return coverage;
    }

    private List<Map<String, Object>> suggestions(AuthorizedScope scope, Map<String, Object> line) {
        List<Map<String, Object>> found = new ArrayList<>();
        String reference = (String) line.get("externalReference");
        String source = (String) line.get("sourceId");
        if (reference != null) {
            found.addAll(jdbc.query(
                    """
                    select m.initiative_id, i.name
                      from actionfinance.initiative_application_map m
                      join actionfinance.initiative i on i.id = m.initiative_id
                     where m.tenant_id = ? and m.company_id = ? and m.application_code in (?, ?)
                    """,
                    (rs, n) -> {
                        Map<String, Object> row = new LinkedHashMap<>();
                        row.put("kind", "INITIATIVE");
                        row.put("strength", "MAPPED");
                        row.put("initiativeId", rs.getObject("initiative_id"));
                        row.put("reason", "Código de aplicação cadastrado para " + rs.getString("name") + ". Confirme antes de atribuir.");
                        return row;
                    },
                    scope.tenantId(), scope.companyId(), reference, source));
        }
        LocalDate when = (LocalDate) line.get("effectiveOn");
        Long net = (Long) line.get("netMinor");
        if (when != null && net != null) {
            found.addAll(jdbc.query(
                    """
                    select id, reference, amount_minor, status
                      from actionfinance.financial_title
                     where tenant_id = ? and company_id = ? and amount_minor = ? and (competence_date = ? or due_date = ?)
                     limit 5
                    """,
                    (rs, n) -> {
                        Map<String, Object> row = new LinkedHashMap<>();
                        row.put("kind", "TITLE");
                        row.put("strength", "WEAK");
                        row.put("titleId", rs.getObject("id", UUID.class));
                        row.put("reference", rs.getString("reference"));
                        row.put("amountMinor", rs.getLong("amount_minor"));
                        row.put("status", rs.getString("status"));
                        row.put("reason", "Mesma data e mesmo valor. Isso não confirma o vínculo.");
                        return row;
                    },
                    scope.tenantId(), scope.companyId(), net, Date.valueOf(when), Date.valueOf(when)));
        }
        return found;
    }

    private LockedLine lockLine(AuthorizedScope scope, UUID lineId) {
        List<LockedLine> rows = jdbc.query(
                """
                select id, account_id, direction, event_kind, effective_on, gross_minor, gross_absent, fee_minor, fee_absent,
                       net_minor, net_absent, balance_effect, availability, import_status, currency_assumed
                  from actionfinance.statement_line
                 where tenant_id = ? and company_id = ? and id = ?
                 for update
                """,
                (rs, n) -> new LockedLine(
                        rs.getObject("id", UUID.class),
                        rs.getObject("account_id", UUID.class),
                        rs.getString("direction"),
                        rs.getString("event_kind"),
                        rs.getObject("effective_on", LocalDate.class),
                        rs.getObject("gross_minor") == null ? null : rs.getLong("gross_minor"),
                        rs.getBoolean("gross_absent"),
                        rs.getObject("fee_minor") == null ? null : rs.getLong("fee_minor"),
                        rs.getBoolean("fee_absent"),
                        rs.getObject("net_minor") == null ? null : rs.getLong("net_minor"),
                        rs.getBoolean("net_absent"),
                        rs.getString("balance_effect"),
                        rs.getString("availability"),
                        rs.getString("import_status"),
                        rs.getBoolean("currency_assumed")),
                scope.tenantId(), scope.companyId(), lineId);
        return rows.isEmpty() ? null : rows.get(0);
    }

    private static Long monetaryBasis(LockedLine line) {
        if (line.netAbsent() || line.netMinor() == null || line.currencyAssumed()) {
            return null;
        }
        return line.netMinor();
    }

    private static long basisAmount(LockedLine line, String basis) {
        return switch (basis) {
            case "GROSS" -> line.grossAbsent() || line.grossMinor() == null ? -1 : line.grossMinor();
            case "NET" -> line.netAbsent() || line.netMinor() == null ? -1 : line.netMinor();
            case "CONFIRMED_PAID" -> -1;
            default -> -1;
        };
    }

    private static String bookBlock(LockedLine line) {
        if (!"ACTIVE".equals(line.importStatus())) {
            return "Este evento foi retirado e não recebe conciliação de caixa.";
        }
        if (line.currencyAssumed()) {
            return "A moeda não está comprovada.";
        }
        if (line.netAbsent() || line.netMinor() == null) {
            return "Não há líquido conhecido para conciliar com o livro.";
        }
        if (!"AFFECTS".equals(line.balanceEffect()) || !"RELEASED".equals(line.availability())) {
            return "Este evento ainda não está liberado como efeito de caixa.";
        }
        return null;
    }

    private MovementRow lockMovement(AuthorizedScope scope, UUID accountId, UUID movementId) {
        jdbc.execute((java.sql.Connection connection) -> {
            try (var statement = connection.prepareStatement("select pg_advisory_xact_lock(hashtext(?))")) {
                statement.setString(1, scope.tenantId() + "|" + scope.companyId() + "|cash-movement|" + movementId);
                statement.execute();
            }
            return null;
        });
        List<MovementRow> rows = jdbc.query(
                """
                select id, signed_amount_minor, kind, settlement_id
                  from actionfinance.cash_movement
                 where tenant_id = ? and company_id = ? and account_id = ? and id = ?
                """,
                (rs, n) -> new MovementRow(
                        rs.getObject("id", UUID.class),
                        rs.getLong("signed_amount_minor"),
                        rs.getString("kind"),
                        rs.getObject("settlement_id", UUID.class)),
                scope.tenantId(), scope.companyId(), accountId, movementId);
        if (rows.isEmpty()) {
            return null;
        }
        MovementRow movement = rows.get(0);
        boolean reversed = false;
        if (movement.settlementId() != null) {
            Integer count = jdbc.queryForObject(
                    "select count(*) from actionfinance.settlement_reversal where tenant_id = ? and company_id = ? and settlement_id = ?",
                    Integer.class, scope.tenantId(), scope.companyId(), movement.settlementId());
            reversed = count != null && count > 0;
        }
        return new MovementRow(movement.id(), movement.signedMinor(), movement.kind(), movement.settlementId(), reversed);
    }

    private long activeBookSum(AuthorizedScope scope, UUID movementId) {
        Long sum = jdbc.queryForObject(
                """
                select coalesce(sum(allocated_minor), 0) from actionfinance.statement_book_allocation
                 where tenant_id = ? and company_id = ? and movement_id = ? and status = 'ACTIVE'
                """,
                Long.class, scope.tenantId(), scope.companyId(), movementId);
        return sum == null ? 0 : sum;
    }

    private long activeBookSigned(AuthorizedScope scope, UUID lineId) {
        Long sum = jdbc.queryForObject(
                """
                select coalesce(sum(movement_sign * allocated_minor), 0) from actionfinance.statement_book_allocation
                 where tenant_id = ? and company_id = ? and line_id = ? and status = 'ACTIVE'
                """,
                Long.class, scope.tenantId(), scope.companyId(), lineId);
        return sum == null ? 0 : sum;
    }

    private long activeReferenceSum(AuthorizedScope scope, UUID lineId, String basis) {
        Long sum = jdbc.queryForObject(
                """
                select coalesce(sum(allocated_minor), 0) from actionfinance.statement_reference_link
                 where tenant_id = ? and company_id = ? and line_id = ? and compared_basis = ? and status = 'ACTIVE'
                """,
                Long.class, scope.tenantId(), scope.companyId(), lineId, basis);
        return sum == null ? 0 : sum;
    }

    private void lockTarget(AuthorizedScope scope, ReferenceCommand command) {
        if ("TITLE".equals(command.targetKind())) {
            List<UUID> locked = jdbc.query(
                    "select id from actionfinance.financial_title where tenant_id = ? and company_id = ? and id = ? for update",
                    (rs, n) -> rs.getObject("id", UUID.class), scope.tenantId(), scope.companyId(), command.titleId());
            if (locked.isEmpty()) {
                throw new ValidationException("Título não encontrado nesta empresa.", Map.of("titleId", "Título não encontrado."));
            }
            return;
        }
        List<UUID> locked = jdbc.query(
                "select id from actionfinance.pay_receipt_transaction where tenant_id = ? and company_id = ? and id = ? for update",
                (rs, n) -> rs.getObject("id", UUID.class), scope.tenantId(), scope.companyId(), command.payReceiptId());
        if (locked.isEmpty()) {
            throw new ValidationException("Recebimento não encontrado nesta empresa.", Map.of("payReceiptId", "Recebimento não encontrado."));
        }
    }

    private long targetLimit(AuthorizedScope scope, ReferenceCommand command) {
        if ("TITLE".equals(command.targetKind())) {
            Long amount = jdbc.queryForObject(
                    "select amount_minor from actionfinance.financial_title where tenant_id = ? and company_id = ? and id = ?",
                    Long.class, scope.tenantId(), scope.companyId(), command.titleId());
            if (amount == null) {
                throw new ValidationException("O título não tem valor para esta base.", Map.of("comparedBasis", "Valor ausente."));
            }
            return amount;
        }
        String column = "CONFIRMED_PAID".equals(command.comparedBasis()) ? "paid_amount_minor" : "amount_minor";
        if ("NET".equals(command.comparedBasis())) {
            throw new ValidationException(
                    "O recebimento integrado não guarda o líquido do extrato. Escolha bruto ou pago confirmado.",
                    Map.of("comparedBasis", "Base incompatível."));
        }
        Long amount = jdbc.queryForObject(
                "select " + column + " from actionfinance.pay_receipt_transaction where tenant_id = ? and company_id = ? and id = ?",
                Long.class, scope.tenantId(), scope.companyId(), command.payReceiptId());
        if (amount == null) {
            throw new ValidationException("Esta base não está informada no recebimento.", Map.of("comparedBasis", "Base ausente."));
        }
        return amount;
    }

    private long activeTargetSum(AuthorizedScope scope, ReferenceCommand command) {
        String column = "TITLE".equals(command.targetKind()) ? "title_id" : "pay_receipt_id";
        UUID id = "TITLE".equals(command.targetKind()) ? command.titleId() : command.payReceiptId();
        Long sum = jdbc.queryForObject(
                """
                select coalesce(sum(allocated_minor), 0) from actionfinance.statement_reference_link
                 where tenant_id = ? and company_id = ? and %s = ? and compared_basis = ? and status = 'ACTIVE'
                """.formatted(column),
                Long.class, scope.tenantId(), scope.companyId(), id, command.comparedBasis());
        return sum == null ? 0 : sum;
    }

    private long decisionVersion(AuthorizedScope scope, UUID lineId) {
        List<Long> rows = jdbc.query(
                "select version from actionfinance.statement_decision where tenant_id = ? and company_id = ? and line_id = ?",
                (rs, n) -> rs.getLong("version"), scope.tenantId(), scope.companyId(), lineId);
        return rows.isEmpty() ? 0 : rows.get(0);
    }

    private UUID decisionId(AuthorizedScope scope, UUID lineId) {
        List<UUID> rows = jdbc.query(
                "select id from actionfinance.statement_decision where tenant_id = ? and company_id = ? and line_id = ?",
                (rs, n) -> rs.getObject("id", UUID.class), scope.tenantId(), scope.companyId(), lineId);
        return rows.isEmpty() ? null : rows.get(0);
    }

    private UUID currentCategory(AuthorizedScope scope, UUID lineId) {
        List<UUID> rows = jdbc.query(
                "select category_id from actionfinance.statement_decision where tenant_id = ? and company_id = ? and line_id = ?",
                (rs, n) -> rs.getObject("category_id", UUID.class), scope.tenantId(), scope.companyId(), lineId);
        return rows.isEmpty() ? null : rows.get(0);
    }

    private String decisionState(AuthorizedScope scope, UUID lineId) {
        List<String> rows = jdbc.query(
                """
                select coalesce(jsonb_build_object(
                    'version', version, 'categoryId', category_id, 'assignment', assignment,
                    'initiativeId', initiative_id, 'ruleVersionId', rule_version_id, 'basisMinor', basis_minor
                )::text, '{}')
                  from actionfinance.statement_decision
                 where tenant_id = ? and company_id = ? and line_id = ?
                """,
                (rs, n) -> rs.getString(1), scope.tenantId(), scope.companyId(), lineId);
        return rows.isEmpty() ? "{}" : rows.get(0);
    }

    private List<Map<String, Object>> shares(AuthorizedScope scope, UUID lineId) {
        return jdbc.query(
                """
                select s.initiative_id, i.name, s.amount_minor, s.criterion
                  from actionfinance.statement_decision_share s
                  join actionfinance.statement_decision d on d.id = s.decision_id
                  left join actionfinance.initiative i on i.id = s.initiative_id
                 where d.tenant_id = ? and d.company_id = ? and d.line_id = ?
                """,
                (rs, n) -> {
                    Map<String, Object> row = new LinkedHashMap<>();
                    row.put("initiativeId", rs.getObject("initiative_id", UUID.class));
                    row.put("name", rs.getString("name") == null ? "Não atribuída" : rs.getString("name"));
                    row.put("amountMinor", rs.getLong("amount_minor"));
                    row.put("criterion", rs.getString("criterion"));
                    return row;
                },
                scope.tenantId(), scope.companyId(), lineId);
    }

    private List<Map<String, Object>> references(AuthorizedScope scope, UUID lineId) {
        return jdbc.query(
                """
                select id, target_kind, title_id, pay_receipt_id, compared_basis, allocated_minor, status, version
                  from actionfinance.statement_reference_link
                 where tenant_id = ? and company_id = ? and line_id = ?
                 order by updated_at desc
                """,
                (rs, n) -> Map.of(
                        "id", rs.getObject("id", UUID.class),
                        "targetKind", rs.getString("target_kind"),
                        "titleId", String.valueOf(rs.getObject("title_id", UUID.class)),
                        "payReceiptId", String.valueOf(rs.getObject("pay_receipt_id", UUID.class)),
                        "comparedBasis", rs.getString("compared_basis"),
                        "allocatedMinor", rs.getLong("allocated_minor"),
                        "status", rs.getString("status"),
                        "version", rs.getLong("version")),
                scope.tenantId(), scope.companyId(), lineId);
    }

    private List<Map<String, Object>> book(AuthorizedScope scope, UUID lineId) {
        return jdbc.query(
                """
                select id, movement_id, group_id, allocated_minor, movement_sign, status, version
                  from actionfinance.statement_book_allocation
                 where tenant_id = ? and company_id = ? and line_id = ?
                 order by updated_at desc
                """,
                (rs, n) -> Map.of(
                        "id", rs.getObject("id", UUID.class),
                        "movementId", rs.getObject("movement_id", UUID.class),
                        "groupId", String.valueOf(rs.getObject("group_id", UUID.class)),
                        "allocatedMinor", rs.getLong("allocated_minor"),
                        "sign", rs.getInt("movement_sign"),
                        "status", rs.getString("status"),
                        "version", rs.getLong("version")),
                scope.tenantId(), scope.companyId(), lineId);
    }

    private List<Map<String, Object>> history(AuthorizedScope scope, UUID lineId) {
        return jdbc.query(
                """
                select link_kind, action, reason, amount_minor, changed_at
                  from actionfinance.statement_link_history
                 where tenant_id = ? and company_id = ? and line_id = ?
                 order by changed_at desc
                """,
                (rs, n) -> Map.of(
                        "kind", rs.getString("link_kind"),
                        "action", rs.getString("action"),
                        "reason", rs.getString("reason"),
                        "amountMinor", rs.getObject("amount_minor") == null ? "" : rs.getLong("amount_minor"),
                        "at", rs.getTimestamp("changed_at").toInstant().toString()),
                scope.tenantId(), scope.companyId(), lineId);
    }

    private List<Map<String, Object>> versions(AuthorizedScope scope, UUID ruleId) {
        return jdbc.query(
                """
                select id, version_no, valid_from, valid_to
                  from actionfinance.allocation_rule_version
                 where tenant_id = ? and company_id = ? and rule_id = ?
                 order by version_no desc
                """,
                (rs, n) -> {
                    Map<String, Object> row = new LinkedHashMap<>();
                    row.put("id", rs.getObject("id", UUID.class));
                    row.put("versionNo", rs.getInt("version_no"));
                    row.put("validFrom", rs.getObject("valid_from", LocalDate.class));
                    row.put("validTo", rs.getObject("valid_to", LocalDate.class));
                    row.put("shares", ruleShares(scope, rs.getObject("id", UUID.class)));
                    return row;
                },
                scope.tenantId(), scope.companyId(), ruleId);
    }

    private UUID insertRuleVersion(
            AuthorizedScope scope, UUID ruleId, int versionNo, LocalDate from, LocalDate to, String note,
            Instant now, UUID actor, List<AllocationMath.Share> shares) {
        UUID versionId = UUID.randomUUID();
        jdbc.update(
                """
                insert into actionfinance.allocation_rule_version (
                    id, tenant_id, company_id, rule_id, version_no, valid_from, valid_to, note, created_at, created_by
                ) values (?,?,?,?,?,?,?,?,?,?)
                """,
                versionId, scope.tenantId(), scope.companyId(), ruleId, versionNo, Date.valueOf(from),
                to == null ? null : Date.valueOf(to), note, Timestamp.from(now), actor);
        for (AllocationMath.Share share : shares) {
            requireInitiative(scope, UUID.fromString(share.initiativeId()));
            jdbc.update(
                    """
                    insert into actionfinance.allocation_rule_share (
                        id, tenant_id, company_id, version_id, initiative_id, basis_points
                    ) values (?,?,?,?,?,?)
                    """,
                    UUID.randomUUID(), scope.tenantId(), scope.companyId(), versionId,
                    UUID.fromString(share.initiativeId()), share.basisPoints());
        }
        return versionId;
    }

    private void assertComplete(List<AllocationMath.Share> shares) {
        if (shares == null || shares.isEmpty()) {
            throw ValidationException.of("shares", "Uma regra completa precisa distribuir 100%.");
        }
        int points = shares.stream().mapToInt(AllocationMath.Share::basisPoints).sum();
        if (points != 10000) {
            throw ValidationException.of("shares", "A soma da regra precisa ser 100%. O restante não atribuído fica na classificação, não numa regra incompleta.");
        }
    }

    private void requireInitiative(AuthorizedScope scope, UUID id) {
        Integer count = jdbc.queryForObject(
                "select count(*) from actionfinance.initiative where tenant_id = ? and company_id = ? and id = ? and active",
                Integer.class, scope.tenantId(), scope.companyId(), id);
        if (count == null || count == 0) {
            throw new ValidationException("Iniciativa ativa não encontrada nesta empresa.", Map.of("initiativeId", "Iniciativa não encontrada."));
        }
    }

    private void insertInitiativeHistory(AuthorizedScope scope, UUID id, long version, String name, boolean active, String reason, Instant now, UUID actor) {
        jdbc.update(
                """
                insert into actionfinance.initiative_history (
                    id, tenant_id, company_id, initiative_id, version, name, active, reason, changed_at, changed_by
                ) values (?,?,?,?,?,?,?,?,?,?)
                """,
                UUID.randomUUID(), scope.tenantId(), scope.companyId(), id, version, name, active, reason, Timestamp.from(now), actor);
    }

    private void linkHistory(AuthorizedScope scope, UUID lineId, String kind, UUID linkId, String action, String reason, Long amount, Instant now, UUID actor) {
        jdbc.update(
                """
                insert into actionfinance.statement_link_history (
                    id, tenant_id, company_id, line_id, link_kind, link_id, action, reason, amount_minor, changed_at, changed_by
                ) values (?,?,?,?,?,?,?,?,?,?,?)
                """,
                UUID.randomUUID(), scope.tenantId(), scope.companyId(), lineId, kind, linkId, action, reason, amount, Timestamp.from(now), actor);
    }

    private Map<String, Object> replay(
            AuthorizedScope scope, ApplicationPrincipal principal, String operation, String key, String canonical, java.util.function.Supplier<Map<String, Object>> action) {
        if (key == null || key.isBlank() || key.length() > 128) {
            throw ValidationException.of("Idempotency-Key", "Informe uma chave de idempotência de até 128 caracteres.");
        }
        String hash = sha(canonical);
        titles.advisoryLock(scope, principal.actorId(), operation, key.trim());
        Optional<IdempotencyRow> existing = titles.findIdempotency(scope, principal.actorId(), operation, key.trim());
        if (existing.isPresent()) {
            if (!existing.get().requestHash().equals(hash)) {
                throw new IdempotencyConflictException();
            }
            try {
                return mapper.readValue(existing.get().bodyJson(), new com.fasterxml.jackson.core.type.TypeReference<>() {});
            } catch (JsonProcessingException exception) {
                throw new IllegalStateException("idempotency-body", exception);
            }
        }
        Map<String, Object> body = action.get();
        titles.insertIdempotency(
                UUID.randomUUID(), scope, principal.actorId(), operation, key.trim(), hash,
                body.get("id") instanceof UUID id ? id : UUID.randomUUID(), 200, json(body), Instant.now(clock));
        return body;
    }

    private String json(Object value) {
        try {
            return mapper.writeValueAsString(value);
        } catch (JsonProcessingException exception) {
            throw new IllegalStateException(exception);
        }
    }

    private static String sha(String text) {
        try {
            return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(text.getBytes(StandardCharsets.UTF_8)));
        } catch (NoSuchAlgorithmException exception) {
            throw new IllegalStateException(exception);
        }
    }

    private static String normalizeCode(String code) {
        String stable = requireText(code, 2, 40, "code", "Informe o código estável da iniciativa.").toUpperCase().replace(' ', '_');
        if (!stable.matches("[A-Z0-9][A-Z0-9_-]{1,39}")) {
            throw ValidationException.of("code", "Use letras, números, hífen ou sublinhado.");
        }
        return stable;
    }

    private static String requireText(String value, int min, int max, String field, String message) {
        String text = value == null ? "" : value.trim();
        if (text.length() < min || text.length() > max) {
            throw ValidationException.of(field, message);
        }
        return text;
    }

    private AuthorizedScope readCatalog(ApplicationPrincipal principal, UUID companyId) {
        access.requirePermission(principal, companyId, FinancePermissions.CATALOGS_READ);
        return access.requireWritable(principal, companyId, FinancePermissions.CATALOGS_READ);
    }

    private AuthorizedScope writeCatalog(ApplicationPrincipal principal, UUID companyId) {
        return access.requireWritable(principal, companyId, FinancePermissions.CATALOGS_WRITE);
    }

    private AuthorizedScope readAccounts(ApplicationPrincipal principal, UUID companyId) {
        access.requirePermission(principal, companyId, FinancePermissions.ACCOUNTS_READ);
        return access.requireWritable(principal, companyId, FinancePermissions.ACCOUNTS_READ);
    }

    private AuthorizedScope writeAccounts(ApplicationPrincipal principal, UUID companyId) {
        return access.requireWritable(principal, companyId, FinancePermissions.ACCOUNTS_WRITE);
    }

    public record ClassifyCommand(
            boolean preview,
            List<UUID> lineIds,
            Map<String, Long> versions,
            UUID categoryId,
            boolean clearCategory,
            String assignment,
            UUID initiativeId,
            UUID ruleVersionId,
            List<AllocationMath.Share> shares,
            LocalDate manualOn,
            String reason) {}

    public record ReferenceCommand(
            UUID lineId,
            String targetKind,
            UUID titleId,
            UUID payReceiptId,
            String comparedBasis,
            long allocatedMinor) {}

    public record BookComponent(UUID movementId, long allocatedMinor) {}

    public record BookCommand(UUID lineId, List<BookComponent> components, boolean allowPartial) {}

    public record UndoCommand(String kind, UUID id, long version, String reason) {}

    private record LockedLine(
            UUID id,
            UUID accountId,
            String direction,
            String eventKind,
            LocalDate effectiveOn,
            Long grossMinor,
            boolean grossAbsent,
            Long feeMinor,
            boolean feeAbsent,
            Long netMinor,
            boolean netAbsent,
            String balanceEffect,
            String availability,
            String importStatus,
            boolean currencyAssumed) {}

    private record MovementRow(UUID id, long signedMinor, String kind, UUID settlementId, boolean reversed) {
        MovementRow(UUID id, long signedMinor, String kind, UUID settlementId) {
            this(id, signedMinor, kind, settlementId, false);
        }
    }
}
