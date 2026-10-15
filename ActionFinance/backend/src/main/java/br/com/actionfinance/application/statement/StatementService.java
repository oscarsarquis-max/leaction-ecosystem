package br.com.actionfinance.application.statement;

import br.com.actionfinance.application.ApplicationPrincipal;
import br.com.actionfinance.application.finance.AuthorizedScope;
import br.com.actionfinance.application.finance.CompanyAccessService;
import br.com.actionfinance.application.finance.FinanceExceptions.IdempotencyConflictException;
import br.com.actionfinance.application.finance.FinanceExceptions.ValidationException;
import br.com.actionfinance.application.finance.FinanceExceptions.VersionConflictException;
import br.com.actionfinance.application.identity.FinancePermissions;
import br.com.actionfinance.application.statement.MpAccountMoneyCsvParser.ParseResult;
import br.com.actionfinance.application.statement.MpAccountMoneyCsvParser.ParsedRow;
import br.com.actionfinance.application.statement.MpAccountMoneyCsvParser.RowIssue;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.dao.DataIntegrityViolationException;
import org.springframework.jdbc.core.SqlParameterValue;
import org.springframework.http.HttpStatus;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.server.ResponseStatusException;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.sql.Timestamp;
import java.sql.Types;
import java.security.NoSuchAlgorithmException;
import java.time.Instant;
import java.time.LocalDate;
import java.time.OffsetDateTime;
import java.util.ArrayList;
import java.util.HexFormat;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.UUID;

@Service
public class StatementService {

    private static final int MAX_BYTES = 512 * 1024;
    private static final TypeReference<List<StoredRow>> ROWS = new TypeReference<>() {};
    private static final TypeReference<List<RowIssue>> ISSUES = new TypeReference<>() {};

    private final JdbcTemplate jdbc;
    private final CompanyAccessService access;
    private final ObjectMapper mapper;

    public StatementService(JdbcTemplate jdbc, CompanyAccessService access, ObjectMapper mapper) {
        this.jdbc = jdbc;
        this.access = access;
        this.mapper = mapper;
    }

    @Transactional
    public LinkView link(ApplicationPrincipal principal, UUID companyId, UUID accountId, String externalRef, String provenance) {
        AuthorizedScope scope = writable(principal, companyId);
        requireSchema();
        String ref = requireText(externalRef, 3, 80, "externalRef", "Informe a referência externa da conta.");
        String why = requireText(provenance, 3, 500, "provenance", "Informe a procedência do vínculo.");
        if (accountId == null || !accountBelongs(scope, accountId)) {
            throw new ValidationException("Conta não encontrada nesta empresa.", Map.of("accountId", "Conta não encontrada nesta empresa."));
        }
        UUID id = UUID.randomUUID();
        try {
            jdbc.update(
                    """
                    insert into actionfinance.external_account_link (
                        id, tenant_id, company_id, account_id, origin_system, external_ref, provenance, created_at, created_by
                    ) values (?, ?, ?, ?, 'MERCADOPAGO', ?, ?, ?, ?)
                    """,
                    id, scope.tenantId(), scope.companyId(), accountId, ref, why, Timestamp.from(Instant.now()), principal.actorId());
        } catch (DataIntegrityViolationException exception) {
            throw new ValidationException("Esta conta ou esta referência já tem vínculo.", Map.of("externalRef", "Vínculo já existente."));
        }
        return new LinkView(id, accountId, ref, why);
    }

    @Transactional
    public PreviewView preview(ApplicationPrincipal principal, UUID companyId, UUID accountId, String fileName, byte[] bytes) {
        AuthorizedScope scope = writable(principal, companyId);
        requireSchema();
        if (accountId == null || !accountBelongs(scope, accountId)) {
            throw new ValidationException("Conta não encontrada nesta empresa.", Map.of("accountId", "Conta não encontrada nesta empresa."));
        }
        LinkRow link = requireLink(scope, accountId);
        if (bytes == null || bytes.length == 0) {
            throw new ValidationException("Envie o arquivo.", Map.of("file", "Arquivo vazio."));
        }
        if (bytes.length > MAX_BYTES) {
            throw new ValidationException("Arquivo acima de 512 KB.", Map.of("file", "Arquivo acima de 512 KB."));
        }
        ParseResult parsed = StatementCsvProfiles.parse(bytes);
        List<StoredRow> stored = new ArrayList<>();
        List<RowIssue> issues = new ArrayList<>(parsed.issues());
        if (parsed.recognized()) {
            for (ParsedRow row : parsed.rows()) {
                StoredRow item = StoredRow.from(row);
                if (row.eligible()) {
                    Existing existing = findLine(scope, accountId, row.eventKey());
                    if (existing != null && !existing.contentHash().equals(row.contentHash())) {
                        if (!canEnrich(existing, item)) {
                            item = item.asIneligible();
                            issues.add(new RowIssue(row.lineNumber(), "IDENTITY_INSUFFICIENT", row.sourceId(), row.recordType(), "A chave já gravada não distingue este conteúdo. O registro conhecido foi preservado e a linha nova fica em revisão."));
                        }
                    }
                }
                stored.add(item);
            }
        }
        boolean accountMatches = parsed.accountColumnPresent()
                && parsed.fileAccountRef() != null
                && parsed.fileAccountRef().equals(link.externalRef());
        boolean confirmBlocked = !parsed.recognized()
                || parsed.currencyAssumed()
                || (parsed.accountColumnPresent() && !accountMatches)
                || stored.isEmpty();
        String blockReason = parsed.fileDiagnostic();
        if (blockReason == null && parsed.accountColumnPresent() && !accountMatches) {
            blockReason = "A conta identificada no arquivo não é a referência vinculada à conta selecionada.";
        }
        String fileHash = sha256(bytes);
        String profileId = parsed.profileId() == null ? "" : parsed.profileId();
        if (!MpAccountMoneyCsvParser.PROFILE.equals(profileId) && !MpSettlementV2CsvParser.PROFILE.equals(profileId)) {
            return new PreviewView(
                    UUID.randomUUID(),
                    "",
                    accountId,
                    link.externalRef(),
                    "unrecognized",
                    false,
                    parsed.fileDiagnostic(),
                    parsed.fileDiagnostic(),
                    true,
                    !parsed.accountColumnPresent(),
                    false,
                    null,
                    null,
                    List.of(),
                    parsed.issues());
        }
        String parserVersion = parsed.parserVersion() == null || parsed.parserVersion().isBlank() ? "0" : parsed.parserVersion();
        String token = sha256(fileHash + "|" + accountId + "|" + link.externalRef() + "|" + profileId + "|" + parserVersion);
        UUID id = UUID.randomUUID();
        jdbc.update(
                """
                insert into actionfinance.statement_batch (
                    id, tenant_id, company_id, account_id, profile_id, parser_version, file_sha256, file_name,
                    status, preview_token, file_account_ref, period_from, period_to, preview_json,
                    created_at, created_by
                ) values (?, ?, ?, ?, ?, ?, ?, ?, 'PREVIEW', ?, ?, ?, ?, ?, ?, ?)
                """,
                id,
                scope.tenantId(),
                scope.companyId(),
                accountId,
                profileId,
                parserVersion,
                fileHash,
                fileName == null || fileName.isBlank() ? "extrato.csv" : fileName.substring(0, Math.min(fileName.length(), 200)),
                token,
                db(parsed.fileAccountRef(), Types.VARCHAR),
                db(parsed.periodFrom(), Types.DATE),
                db(parsed.periodTo(), Types.DATE),
                json(Map.of("rows", stored, "issues", issues, "diagnostic", parsed.fileDiagnostic() == null ? "" : parsed.fileDiagnostic(), "currencyAssumed", parsed.currencyAssumed(), "accountColumn", parsed.accountColumnPresent())),
                Timestamp.from(Instant.now()),
                principal.actorId());
        return new PreviewView(
                id,
                token,
                accountId,
                link.externalRef(),
                profileId,
                parsed.recognized(),
                parsed.fileDiagnostic(),
                blockReason,
                confirmBlocked,
                !parsed.accountColumnPresent(),
                parsed.currencyAssumed(),
                parsed.periodFrom(),
                parsed.periodTo(),
                stored,
                issues);
    }

    @Transactional
    public ConfirmView confirm(
            ApplicationPrincipal principal,
            UUID companyId,
            UUID previewId,
            String previewToken,
            List<Integer> lineNumbers,
            String accountEvidence,
            String idempotencyKey) {
        AuthorizedScope scope = writable(principal, companyId);
        requireSchema();
        if (lineNumbers == null) {
            lineNumbers = List.of();
        }
        String key = requireText(idempotencyKey, 8, 80, "Idempotency-Key", "Informe a chave de idempotência.");
        BatchRow existingKey = findByIdempotency(scope, key);
        if (existingKey != null) {
            if (!existingKey.previewId().equals(previewId) || !existingKey.selectionSha().equals(sha256(selectionCanon(lineNumbers)))) {
                throw new IdempotencyConflictException();
            }
            return existingKey.result();
        }
        BatchRow batch = lockBatch(scope, previewId);
        if (batch == null) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "Prévia não encontrada.");
        }
        if (!"PREVIEW".equals(batch.status())) {
            throw new VersionConflictException("Esta prévia já foi confirmada ou retirada.");
        }
        if (previewToken == null || !previewToken.equals(batch.previewToken())) {
            throw new VersionConflictException("A prévia está obsoleta. Gere outra antes de confirmar.");
        }
        LinkRow link = requireLink(scope, batch.accountId());
        Map<String, Object> preview = readJson(batch.previewJson());
        List<StoredRow> rows = mapper.convertValue(preview.get("rows"), ROWS);
        boolean accountColumn = Boolean.TRUE.equals(preview.get("accountColumn"));
        if (Boolean.TRUE.equals(preview.get("currencyAssumed"))) {
            throw new ValidationException(
                    "A moeda não está comprovada. Nenhuma linha foi gravada e nenhuma soma foi atualizada.",
                    Map.of("file", "Moeda ausente."));
        }
        String evidence = accountEvidence == null ? "" : accountEvidence.trim();
        if (!accountColumn && evidence.length() < 10) {
            throw new ValidationException(
                    "O arquivo não identifica a conta. Registre a declaração do operador. Isso não valida a conta no Mercado Pago.",
                    Map.of("accountEvidence", "Declaração do operador. Não é validação automática."));
        }
        if (accountColumn && (batch.fileAccountRef() == null || !batch.fileAccountRef().equals(link.externalRef()))) {
            throw new ValidationException("A conta do arquivo não confere com o vínculo.", Map.of("accountId", "Conta divergente."));
        }
        if (lineNumbers == null) {
            lineNumbers = List.of();
        }
        Map<Integer, StoredRow> byNumber = new LinkedHashMap<>();
        for (StoredRow row : rows) {
            byNumber.put(row.lineNumber(), row);
        }
        List<StoredRow> selected = new ArrayList<>();
        for (Integer number : lineNumbers) {
            StoredRow row = byNumber.get(number);
            if (row == null || !row.eligible()) {
                throw new ValidationException("Há linha selecionada que não é elegível.", Map.of("lineNumbers", "Linha " + number + " não pode ser confirmada."));
            }
            Existing current = findLine(scope, batch.accountId(), row.eventKey());
            if (current != null && !current.contentHash().equals(row.contentHash()) && !canEnrich(current, row)) {
                throw new VersionConflictException("A chave não distingue o conteúdo novo do já gravado. Nada foi alterado.");
            }
            selected.add(row);
        }
        int created = 0;
        int enriched = 0;
        int unchanged = 0;
        Map<Integer, UUID> consolidated = new LinkedHashMap<>();
        Timestamp now = Timestamp.from(Instant.now());
        for (StoredRow row : selected) {
            Existing current = findLine(scope, batch.accountId(), row.eventKey());
            if (current == null) {
                UUID lineId = UUID.randomUUID();
                consolidated.put(row.lineNumber(), lineId);
                jdbc.update(
                        """
                        insert into actionfinance.statement_line (
                            id, tenant_id, company_id, account_id, batch_id, event_key, content_hash, source_id, record_type,
                            external_reference, description, effective_on, direction, event_kind, balance_effect,
                            gross_minor, gross_absent, fee_minor, fee_absent, net_minor, net_absent, currency, currency_assumed, availability,
                            classification_state, initiative_state, import_status, source_line_number, created_at, updated_at
                        ) values (
                            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'BRL', ?, ?, 'UNCLASSIFIED', 'UNASSIGNED', 'ACTIVE', ?, ?, ?
                        )
                        """,
                        lineId, scope.tenantId(), scope.companyId(), batch.accountId(), batch.previewId(), row.eventKey(), row.contentHash(),
                        row.sourceId(), row.recordType(), db(row.externalReference(), Types.VARCHAR), db(row.description(), Types.VARCHAR), db(row.effectiveOn(), Types.DATE), row.direction(),
                        row.eventKind(), row.balanceEffect(), db(row.grossMinor(), Types.NUMERIC), row.grossAbsent(), db(row.feeMinor(), Types.NUMERIC), row.feeAbsent(),
                        db(row.netMinor(), Types.NUMERIC), row.netAbsent(), row.currencyAssumed(), row.availability(), row.lineNumber(), now, now);
                insertOriginal(scope, lineId, batch.previewId(), row, now);
                created++;
            } else if (!fills(current, row)) {
                consolidated.put(row.lineNumber(), current.id());
                unchanged++;
            } else {
                consolidated.put(row.lineNumber(), current.id());
                jdbc.update(
                        """
                        update actionfinance.statement_line
                           set content_hash = ?, external_reference = coalesce(external_reference, ?),
                               description = coalesce(description, ?), effective_on = coalesce(effective_on, ?),
                               gross_minor = coalesce(gross_minor, ?), gross_absent = case when gross_minor is null then ? else gross_absent end,
                               fee_minor = coalesce(fee_minor, ?), fee_absent = case when fee_minor is null then ? else fee_absent end,
                               net_minor = coalesce(net_minor, ?), net_absent = case when net_minor is null then ? else net_absent end,
                               updated_at = ?
                         where tenant_id = ? and company_id = ? and id = ?
                        """,
                        mergedHash(current, row),
                        db(row.externalReference(), Types.VARCHAR), db(row.description(), Types.VARCHAR), db(row.effectiveOn(), Types.DATE),
                        db(row.grossMinor(), Types.NUMERIC), row.grossAbsent(), db(row.feeMinor(), Types.NUMERIC), row.feeAbsent(), db(row.netMinor(), Types.NUMERIC), row.netAbsent(), now,
                        scope.tenantId(), scope.companyId(), current.id());
                insertOriginal(scope, current.id(), batch.previewId(), row, now);
                enriched++;
            }
        }
        List<RowIssue> issues = preview.get("issues") == null
                ? List.of()
                : mapper.convertValue(preview.get("issues"), ISSUES);
        String profileId = jdbc.queryForObject(
                "select profile_id from actionfinance.statement_batch where tenant_id = ? and company_id = ? and id = ?",
                String.class, scope.tenantId(), scope.companyId(), batch.previewId());
        String fileSha = jdbc.queryForObject(
                "select file_sha256 from actionfinance.statement_batch where tenant_id = ? and company_id = ? and id = ?",
                String.class, scope.tenantId(), scope.companyId(), batch.previewId());
        int inReview = persistOccurrences(scope, batch, rows, issues, consolidated, profileId, fileSha, now);
        long eligibleNotSelected = Math.max(0, rows.stream().filter(StoredRow::eligible).count() - selected.size());
        int rejected = (int) rows.stream().filter(row -> !row.eligible()).count() + (int) eligibleNotSelected;
        String attestation = accountColumn ? "FILE_REFERENCE" : "OPERATOR_DECLARATION";
        ConfirmView result = new ConfirmView(
                batch.previewId(), created, enriched, unchanged, rejected, rows.size(), inReview,
                "Total parcial das linhas elegíveis. Não é o fluxo integral da conta, nem variação de saldo, nem disponível.",
                attestation);
        jdbc.update(
                """
                update actionfinance.statement_batch
                   set status = 'CONFIRMED', result_json = ?, confirm_idempotency_key = ?, selection_sha256 = ?,
                       account_evidence = ?, created_count = ?, enriched_count = ?, unchanged_count = ?, rejected_count = ?,
                       confirmed_at = ?, confirmed_by = ?
                 where tenant_id = ? and company_id = ? and id = ?
                """,
                json(result), key, sha256(selectionCanon(lineNumbers)), db(evidence.isBlank() ? null : evidence, Types.VARCHAR),
                created, enriched, unchanged, rejected, now, principal.actorId(),
                scope.tenantId(), scope.companyId(), batch.previewId());
        return result;
    }

    @Transactional
    public void withdraw(ApplicationPrincipal principal, UUID companyId, UUID batchId, String reason) {
        AuthorizedScope scope = writable(principal, companyId);
        requireSchema();
        String why = requireText(reason, 3, 500, "reason", "Informe o motivo da retirada.");
        BatchRow batch = lockBatch(scope, batchId);
        if (batch == null || !"CONFIRMED".equals(batch.status())) {
            throw new ValidationException("Só um lote confirmado pode ser retirado.", Map.of("batchId", "Lote indisponível."));
        }
        Timestamp now = Timestamp.from(Instant.now());
        jdbc.update(
                """
                update actionfinance.statement_batch
                   set status = 'WITHDRAWN', withdrawn_at = ?, withdrawn_by = ?, withdraw_reason = ?
                 where tenant_id = ? and company_id = ? and id = ?
                """,
                now, principal.actorId(), why, scope.tenantId(), scope.companyId(), batchId);
        jdbc.update(
                """
                update actionfinance.statement_line
                   set import_status = 'WITHDRAWN', updated_at = ?
                 where tenant_id = ? and company_id = ? and batch_id = ? and import_status = 'ACTIVE'
                """,
                now, scope.tenantId(), scope.companyId(), batchId);
    }

    @Transactional(readOnly = true)
    public Map<String, Object> lines(
            ApplicationPrincipal principal,
            UUID companyId,
            UUID accountId,
            LocalDate from,
            LocalDate to,
            String direction,
            String eventKind,
            String importStatus,
            String suggestion,
            int page,
            int size) {
        AuthorizedScope scope = readable(principal, companyId);
        requireSchema();
        if (accountId != null && !accountBelongs(scope, accountId)) {
            throw new ValidationException("Conta não encontrada nesta empresa.", Map.of("accountId", "Conta não encontrada nesta empresa."));
        }
        List<Object> args = new ArrayList<>();
        StringBuilder where = new StringBuilder(" where tenant_id = ? and company_id = ? ");
        args.add(scope.tenantId());
        args.add(scope.companyId());
        if (accountId != null) {
            where.append(" and account_id = ? ");
            args.add(accountId);
        }
        if (from != null) {
            where.append(" and effective_on >= ? ");
            args.add(from);
        }
        if (to != null) {
            where.append(" and effective_on <= ? ");
            args.add(to);
        }
        if (direction != null && !direction.isBlank()) {
            where.append(" and direction = ? ");
            args.add(direction);
        }
        if (eventKind != null && !eventKind.isBlank()) {
            where.append(" and event_kind = ? ");
            args.add(eventKind);
        }
        if (importStatus != null && !importStatus.isBlank()) {
            where.append(" and import_status = ? ");
            args.add(importStatus);
        }
        List<LineView> all = jdbc.query(
                "select * from actionfinance.statement_line " + where + " order by effective_on desc nulls last, id desc",
                (rs, n) -> mapLine(rs),
                args.toArray());
        List<LineView> filtered = new ArrayList<>();
        for (LineView line : all) {
            List<SuggestionView> suggestions = suggestions(scope, line);
            LineView with = line.withSuggestions(suggestions);
            if (suggestion == null || suggestion.isBlank() || matchesSuggestion(suggestion, suggestions)) {
                filtered.add(with);
            }
        }
        long credit = 0;
        int creditCount = 0;
        long debit = 0;
        int debitCount = 0;
        int availability = 0;
        int absent = 0;
        int excluded = 0;
        for (LineView line : filtered) {
            if (!"ACTIVE".equals(line.importStatus())) {
                continue;
            }
            if ("AVAILABILITY_ONLY".equals(line.balanceEffect())) {
                availability++;
                continue;
            }
            if (!"AFFECTS".equals(line.balanceEffect()) || line.netAbsent()) {
                if (line.netAbsent()) {
                    absent++;
                } else {
                    excluded++;
                }
                continue;
            }
            if ("IN".equals(line.direction())) {
                credit += line.netMinor();
                creditCount++;
            } else if ("OUT".equals(line.direction())) {
                debit += line.netMinor();
                debitCount++;
            }
        }
        int fromIndex = Math.max(page, 0) * size;
        int toIndex = Math.min(fromIndex + size, filtered.size());
        List<LineView> pageItems = fromIndex >= filtered.size() ? List.of() : filtered.subList(fromIndex, toIndex);
        Map<String, Object> body = new LinkedHashMap<>();
        body.put("page", page);
        body.put("size", size);
        body.put("total", filtered.size());
        body.put("creditMinor", Long.toString(credit));
        body.put("creditCount", creditCount);
        body.put("debitMinor", Long.toString(debit));
        body.put("debitCount", debitCount);
        body.put("availabilityCount", availability);
        body.put("amountAbsentCount", absent);
        body.put("excludedFromPartialCount", excluded);
        body.put("reviewCount", reviewCount(scope, accountId));
        body.put("totalBasis", "PARTIAL_ELIGIBLE");
        body.put("totalBasisText", "Total parcial das linhas elegíveis. Não é o fluxo integral da conta. Não é variação do saldo total nem do disponível.");
        body.put("items", pageItems);
        body.put("imported", countImported(scope, accountId));
        return body;
    }

    @Transactional(readOnly = true)
    public LineView line(ApplicationPrincipal principal, UUID companyId, UUID lineId) {
        AuthorizedScope scope = readable(principal, companyId);
        requireSchema();
        List<LineView> found = jdbc.query(
                "select * from actionfinance.statement_line where tenant_id = ? and company_id = ? and id = ?",
                (rs, n) -> mapLine(rs),
                scope.tenantId(), scope.companyId(), lineId);
        if (found.isEmpty()) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "Linha não encontrada.");
        }
        LineView line = found.get(0).withSuggestions(suggestions(scope, found.get(0)));
        List<String> raws = jdbc.query(
                "select raw_text from actionfinance.statement_original_row where tenant_id = ? and company_id = ? and line_id = ? order by created_at",
                (rs, n) -> rs.getString(1),
                scope.tenantId(), scope.companyId(), lineId);
        return line.withOriginal(raws);
    }

    @Transactional(readOnly = true)
    public List<Map<String, Object>> batches(ApplicationPrincipal principal, UUID companyId, UUID accountId) {
        AuthorizedScope scope = readable(principal, companyId);
        requireSchema();
        return jdbc.query(
                """
                select id, account_id, file_name, status, profile_id, period_from, period_to,
                       created_count, enriched_count, unchanged_count, rejected_count, created_at, confirmed_at, withdraw_reason
                  from actionfinance.statement_batch
                 where tenant_id = ? and company_id = ? and (?::uuid is null or account_id = ?)
                 order by created_at desc
                 limit 50
                """,
                (rs, n) -> {
                    Map<String, Object> row = new LinkedHashMap<>();
                    row.put("id", rs.getObject("id", UUID.class));
                    row.put("accountId", rs.getObject("account_id", UUID.class));
                    row.put("fileName", rs.getString("file_name"));
                    row.put("status", rs.getString("status"));
                    row.put("profileId", rs.getString("profile_id"));
                    row.put("periodFrom", rs.getObject("period_from", LocalDate.class));
                    row.put("periodTo", rs.getObject("period_to", LocalDate.class));
                    row.put("createdCount", rs.getInt("created_count"));
                    row.put("enrichedCount", rs.getInt("enriched_count"));
                    row.put("unchangedCount", rs.getInt("unchanged_count"));
                    row.put("rejectedCount", rs.getInt("rejected_count"));
                    row.put("createdAt", rs.getObject("created_at", OffsetDateTime.class));
                    row.put("confirmedAt", rs.getObject("confirmed_at", OffsetDateTime.class));
                    row.put("withdrawReason", rs.getString("withdraw_reason"));
                    return row;
                },
                scope.tenantId(), scope.companyId(), accountId, accountId);
    }

    @Transactional(readOnly = true)
    public Map<String, Object> batch(ApplicationPrincipal principal, UUID companyId, UUID batchId) {
        AuthorizedScope scope = readable(principal, companyId);
        requireSchema();
        List<Map<String, Object>> header = jdbc.query(
                """
                select id, account_id, file_name, file_sha256, status, profile_id, period_from, period_to,
                       created_count, enriched_count, unchanged_count, rejected_count
                  from actionfinance.statement_batch
                 where tenant_id = ? and company_id = ? and id = ?
                """,
                (rs, n) -> {
                    Map<String, Object> row = new LinkedHashMap<>();
                    row.put("id", rs.getObject("id", UUID.class));
                    row.put("accountId", rs.getObject("account_id", UUID.class));
                    row.put("fileName", rs.getString("file_name"));
                    row.put("fileSha256", rs.getString("file_sha256"));
                    row.put("status", rs.getString("status"));
                    row.put("profileId", rs.getString("profile_id"));
                    row.put("periodFrom", rs.getObject("period_from", LocalDate.class));
                    row.put("periodTo", rs.getObject("period_to", LocalDate.class));
                    row.put("createdCount", rs.getInt("created_count"));
                    row.put("enrichedCount", rs.getInt("enriched_count"));
                    row.put("unchangedCount", rs.getInt("unchanged_count"));
                    row.put("inReviewCount", rs.getInt("rejected_count"));
                    return row;
                },
                scope.tenantId(), scope.companyId(), batchId);
        if (header.isEmpty()) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "Lote não encontrado.");
        }
        Map<String, Object> body = header.get(0);
        if (!accountBelongs(scope, (UUID) body.get("accountId"))) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "Lote não encontrado.");
        }
        List<Map<String, Object>> occurrences = jdbc.query(
                """
                select source_line_number, availability, consolidation, exclusion_code, in_partial_total, line_id,
                       source_id, record_type, description, effective_on, direction, event_kind,
                       gross_minor, gross_absent, fee_minor, fee_absent, net_minor, net_absent, event_key
                  from actionfinance.statement_occurrence
                 where tenant_id = ? and company_id = ? and batch_id = ?
                 order by source_line_number
                """,
                (rs, n) -> {
                    Map<String, Object> row = new LinkedHashMap<>();
                    row.put("lineNumber", rs.getInt("source_line_number"));
                    row.put("availability", rs.getString("availability"));
                    row.put("consolidation", rs.getString("consolidation"));
                    row.put("exclusionCode", rs.getString("exclusion_code"));
                    row.put("inPartialTotal", rs.getBoolean("in_partial_total"));
                    row.put("lineId", rs.getObject("line_id", UUID.class));
                    row.put("sourceId", rs.getString("source_id"));
                    row.put("recordType", rs.getString("record_type"));
                    row.put("description", rs.getString("description"));
                    row.put("effectiveOn", rs.getObject("effective_on", LocalDate.class));
                    row.put("direction", rs.getString("direction"));
                    row.put("eventKind", rs.getString("event_kind"));
                    row.put("grossMinor", rs.getObject("gross_minor") == null ? null : rs.getLong("gross_minor"));
                    row.put("grossAbsent", rs.getBoolean("gross_absent"));
                    row.put("feeMinor", rs.getObject("fee_minor") == null ? null : rs.getLong("fee_minor"));
                    row.put("feeAbsent", rs.getBoolean("fee_absent"));
                    row.put("netMinor", rs.getObject("net_minor") == null ? null : rs.getLong("net_minor"));
                    row.put("netAbsent", rs.getBoolean("net_absent"));
                    row.put("eventIdentified", rs.getString("event_key") != null);
                    return row;
                },
                scope.tenantId(), scope.companyId(), batchId);
        body.put("occurrences", occurrences);
        body.put("preservedCount", occurrences.size());
        body.put("consolidatedCount", occurrences.stream().filter(row -> "CONSOLIDATED".equals(row.get("consolidation"))).count());
        body.put("partialCount", occurrences.stream().filter(row -> Boolean.TRUE.equals(row.get("inPartialTotal"))).count());
        body.put("partialTotalText", "Total parcial das linhas elegíveis. Não é o fluxo integral da conta. Não é variação do saldo total nem do disponível.");
        body.put("documentIdentityText", "A posição no arquivo identifica a ocorrência deste lote. Não prova o evento financeiro entre importações.");
        return body;
    }

    private List<SuggestionView> suggestions(AuthorizedScope scope, LineView line) {
        List<SuggestionView> found = new ArrayList<>();
        if (line.sourceId() != null) {
            found.addAll(jdbc.query(
                    """
                    select id, transaction_id, amount_minor, paid_amount_minor, paid_amount_absent, currency
                      from actionfinance.pay_receipt_transaction
                     where tenant_id = ? and company_id = ? and processor_reference = ?
                    """,
                    (rs, n) -> suggestion(rs, "QUALIFIED", "MP_PAYMENT", "A referência do pagamento no extrato coincide com a referência do processador no recebimento.", line),
                    scope.tenantId(), scope.companyId(), line.sourceId()));
        }
        if (line.externalReference() != null) {
            found.addAll(jdbc.query(
                    """
                    select id, transaction_id, amount_minor, paid_amount_minor, paid_amount_absent, currency
                      from actionfinance.pay_receipt_transaction
                     where tenant_id = ? and company_id = ? and (transaction_id = ? or order_reference = ?)
                    """,
                    (rs, n) -> suggestion(rs, "QUALIFIED", "ORDER", "Referência externa igual à referência do recebimento.", line),
                    scope.tenantId(), scope.companyId(), line.externalReference(), line.externalReference()));
        }
        if (!found.isEmpty() || line.netAbsent() || line.effectiveOn() == null || !"AFFECTS".equals(line.balanceEffect())) {
            return found;
        }
        List<SuggestionView> weak = jdbc.query(
                """
                select id, transaction_id, amount_minor, paid_amount_minor, paid_amount_absent, currency
                  from actionfinance.pay_receipt_transaction
                 where tenant_id = ? and company_id = ?
                   and ((paid_amount_absent = false and paid_amount_minor = ?) or (amount_absent = false and amount_minor = ?))
                   and origin_updated_at::date = ?
                """,
                (rs, n) -> suggestion(rs, "WEAK", "AMOUNT_DATE", "Mesma data e mesmo valor, sem referência em comum. Não é confirmação.", line),
                scope.tenantId(), scope.companyId(), line.netMinor(), line.netMinor(), line.effectiveOn());
        return weak.size() == 1 ? weak : List.of();
    }

    private SuggestionView suggestion(java.sql.ResultSet rs, String strength, String namespace, String reason, LineView line) throws java.sql.SQLException {
        List<String> divergence = new ArrayList<>();
        String currency = rs.getString("currency");
        if (currency != null && !"BRL".equals(currency)) {
            divergence.add("Moeda do recebimento diferente de BRL.");
        }
        long net = line.netMinor() == null ? -1 : line.netMinor();
        boolean paidAbsent = rs.getBoolean("paid_amount_absent");
        Long paid = rs.getObject("paid_amount_minor") == null ? null : rs.getLong("paid_amount_minor");
        if (!paidAbsent && paid != null && net >= 0 && paid != net) {
            divergence.add("Líquido do extrato difere do pago do recebimento.");
        }
        return new SuggestionView(rs.getObject("id", UUID.class), strength, namespace, reason, String.join(" ", divergence));
    }

    private static boolean matchesSuggestion(String filter, List<SuggestionView> suggestions) {
        return switch (filter) {
            case "QUALIFIED" -> suggestions.stream().anyMatch(item -> "QUALIFIED".equals(item.strength()));
            case "WEAK" -> suggestions.stream().anyMatch(item -> "WEAK".equals(item.strength()));
            case "NONE" -> suggestions.isEmpty();
            default -> true;
        };
    }

    private static boolean canEnrich(Existing current, StoredRow incoming) {
        return !contradicts(current, incoming);
    }

    private static boolean contradicts(Existing current, StoredRow incoming) {
        return differs(current.externalReference(), incoming.externalReference())
                || differs(current.description(), incoming.description())
                || differs(current.effectiveOn(), incoming.effectiveOn())
                || differs(current.grossMinor(), incoming.grossMinor())
                || differs(current.feeMinor(), incoming.feeMinor())
                || differs(current.netMinor(), incoming.netMinor())
                || !current.direction().equals(incoming.direction());
    }

    private static boolean fills(Existing current, StoredRow incoming) {
        return fills(current.externalReference(), incoming.externalReference())
                || fills(current.description(), incoming.description())
                || fills(current.effectiveOn(), incoming.effectiveOn())
                || fills(current.grossMinor(), incoming.grossMinor())
                || fills(current.feeMinor(), incoming.feeMinor())
                || fills(current.netMinor(), incoming.netMinor());
    }

    private static boolean differs(Object current, Object incoming) {
        return current != null && incoming != null && !current.equals(incoming);
    }

    private static boolean fills(Object current, Object incoming) {
        return current == null && incoming != null;
    }

    private static String mergedHash(Existing current, StoredRow incoming) {
        String external = first(current.externalReference(), incoming.externalReference());
        String description = first(current.description(), incoming.description());
        LocalDate effective = current.effectiveOn() != null ? current.effectiveOn() : incoming.effectiveOn();
        Long gross = current.grossMinor() != null ? current.grossMinor() : incoming.grossMinor();
        Long fee = current.feeMinor() != null ? current.feeMinor() : incoming.feeMinor();
        Long net = current.netMinor() != null ? current.netMinor() : incoming.netMinor();
        return MpAccountMoneyCsvParser.sha256(String.join("|",
                incoming.sourceId(),
                incoming.recordType(),
                external == null ? "" : external,
                effective == null ? "" : effective.toString(),
                current.direction(),
                gross == null ? "" : Long.toString(gross),
                fee == null ? "" : Long.toString(fee),
                net == null ? "" : Long.toString(net),
                "BRL",
                description == null ? "" : description));
    }

    private static String first(String current, String incoming) {
        return current != null ? current : incoming;
    }

    private int persistOccurrences(
            AuthorizedScope scope,
            BatchRow batch,
            List<StoredRow> rows,
            List<RowIssue> issues,
            Map<Integer, UUID> consolidated,
            String profileId,
            String fileSha,
            Timestamp now) {
        boolean settlement = MpSettlementV2CsvParser.PROFILE.equals(profileId);
        int inReview = 0;
        for (StoredRow row : rows) {
            boolean identity = issues.stream().anyMatch(issue -> issue.lineNumber() == row.lineNumber() && "IDENTITY_INSUFFICIENT".equals(issue.code()));
            boolean duplicate = issues.stream().anyMatch(issue -> issue.lineNumber() == row.lineNumber() && "DUPLICATE".equals(issue.code()));
            boolean consolidatedRow = consolidated.containsKey(row.lineNumber()) && !identity;
            UUID lineId = consolidated.get(row.lineNumber());
            if (lineId == null && !identity && row.eventKey() != null) {
                Existing existing = findLine(scope, batch.accountId(), row.eventKey());
                if (existing != null && existing.contentHash().equals(row.contentHash())) {
                    lineId = existing.id();
                }
            }
            String consolidation = consolidatedRow ? "CONSOLIDATED" : "IN_REVIEW";
            if (!consolidatedRow) {
                inReview++;
            }
            boolean partial = consolidatedRow
                    && "AFFECTS".equals(row.balanceEffect())
                    && ("RELEASED".equals(row.availability()) || (!settlement && "UNKNOWN".equals(row.availability())));
            String exclusion = null;
            if (identity) {
                exclusion = "IDENTITY_INSUFFICIENT";
            } else if (duplicate) {
                exclusion = "DUPLICATE";
            } else if (!consolidatedRow) {
                exclusion = "NOT_SELECTED";
            } else if (!partial) {
                exclusion = "UNRELEASED".equals(row.availability()) ? "UNRELEASED" : "OUT_OF_TOTAL";
            }
            jdbc.update(
                    """
                    insert into actionfinance.statement_occurrence (
                        id, tenant_id, company_id, batch_id, source_line_number, document_key, event_key, content_hash,
                        availability, consolidation, exclusion_code, in_partial_total, line_id, source_id, record_type,
                        description, effective_on, direction, event_kind, gross_minor, gross_absent, fee_minor, fee_absent,
                        net_minor, net_absent, raw_text, truncated, created_at
                    ) values (
                        ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                    )
                    """,
                    UUID.randomUUID(), scope.tenantId(), scope.companyId(), batch.previewId(), row.lineNumber(),
                    fileSha + ":" + row.lineNumber(),
                    identity ? null : row.eventKey(),
                    row.contentHash(),
                    row.availability() == null ? "UNKNOWN" : row.availability(),
                    consolidation,
                    exclusion,
                    partial,
                    db(lineId, Types.OTHER),
                    row.sourceId() == null ? "" : row.sourceId(),
                    row.recordType() == null ? "" : row.recordType(),
                    db(row.description(), Types.VARCHAR),
                    db(row.effectiveOn(), Types.DATE),
                    row.direction(),
                    row.eventKind(),
                    db(row.grossMinor(), Types.NUMERIC), row.grossAbsent(),
                    db(row.feeMinor(), Types.NUMERIC), row.feeAbsent(),
                    db(row.netMinor(), Types.NUMERIC), row.netAbsent(),
                    row.rawText(), row.truncated(), now);
        }
        return inReview;
    }

    private void insertOriginal(AuthorizedScope scope, UUID lineId, UUID batchId, StoredRow row, Timestamp now) {
        jdbc.update(
                """
                insert into actionfinance.statement_original_row (
                    id, tenant_id, company_id, line_id, batch_id, source_line_number, raw_text, truncated, created_at
                ) values (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                UUID.randomUUID(), scope.tenantId(), scope.companyId(), lineId, batchId, row.lineNumber(), row.rawText(), row.truncated(), now);
    }

    private Existing findLine(AuthorizedScope scope, UUID accountId, String eventKey) {
        List<Existing> found = jdbc.query(
                """
                select id, content_hash, external_reference, description, effective_on, direction,
                       gross_minor, fee_minor, net_minor
                  from actionfinance.statement_line
                 where tenant_id = ? and company_id = ? and account_id = ? and event_key = ?
                """,
                (rs, n) -> new Existing(
                        rs.getObject("id", UUID.class),
                        rs.getString("content_hash"),
                        rs.getString("external_reference"),
                        rs.getString("description"),
                        rs.getObject("effective_on", LocalDate.class),
                        rs.getString("direction"),
                        rs.getObject("gross_minor") == null ? null : rs.getLong("gross_minor"),
                        rs.getObject("fee_minor") == null ? null : rs.getLong("fee_minor"),
                        rs.getObject("net_minor") == null ? null : rs.getLong("net_minor")),
                scope.tenantId(), scope.companyId(), accountId, eventKey);
        return found.isEmpty() ? null : found.get(0);
    }

    private boolean accountBelongs(AuthorizedScope scope, UUID accountId) {
        Integer count = jdbc.queryForObject(
                "select count(*) from actionfinance.financial_account where tenant_id = ? and company_id = ? and id = ?",
                Integer.class,
                scope.tenantId(), scope.companyId(), accountId);
        return count != null && count == 1;
    }

    private LinkRow requireLink(AuthorizedScope scope, UUID accountId) {
        List<LinkRow> found = jdbc.query(
                """
                select external_ref from actionfinance.external_account_link
                 where tenant_id = ? and company_id = ? and account_id = ? and origin_system = 'MERCADOPAGO'
                """,
                (rs, n) -> new LinkRow(rs.getString(1)),
                scope.tenantId(), scope.companyId(), accountId);
        if (found.isEmpty()) {
            throw new ValidationException(
                    "Vincule a referência externa da conta antes de importar.",
                    Map.of("accountId", "Conta sem referência externa."));
        }
        return found.get(0);
    }

    private BatchRow lockBatch(AuthorizedScope scope, UUID id) {
        List<BatchRow> found = jdbc.query(
                """
                select id, account_id, status, preview_token, file_account_ref, preview_json, selection_sha256, result_json
                  from actionfinance.statement_batch
                 where tenant_id = ? and company_id = ? and id = ?
                 for update
                """,
                (rs, n) -> new BatchRow(
                        rs.getObject("id", UUID.class),
                        rs.getObject("account_id", UUID.class),
                        rs.getString("status"),
                        rs.getString("preview_token"),
                        rs.getString("file_account_ref"),
                        rs.getString("preview_json"),
                        rs.getString("selection_sha256"),
                        rs.getString("result_json")),
                scope.tenantId(), scope.companyId(), id);
        return found.isEmpty() ? null : found.get(0);
    }

    private BatchRow findByIdempotency(AuthorizedScope scope, String key) {
        List<BatchRow> found = jdbc.query(
                """
                select id, account_id, status, preview_token, file_account_ref, preview_json, selection_sha256, result_json
                  from actionfinance.statement_batch
                 where tenant_id = ? and company_id = ? and confirm_idempotency_key = ?
                """,
                (rs, n) -> new BatchRow(
                        rs.getObject("id", UUID.class),
                        rs.getObject("account_id", UUID.class),
                        rs.getString("status"),
                        rs.getString("preview_token"),
                        rs.getString("file_account_ref"),
                        rs.getString("preview_json"),
                        rs.getString("selection_sha256"),
                        rs.getString("result_json")),
                scope.tenantId(), scope.companyId(), key);
        return found.isEmpty() ? null : found.get(0);
    }

    private int reviewCount(AuthorizedScope scope, UUID accountId) {
        Integer count = jdbc.queryForObject(
                """
                select count(*)
                  from actionfinance.statement_occurrence occurrence
                  join actionfinance.statement_batch batch
                    on batch.tenant_id = occurrence.tenant_id
                   and batch.company_id = occurrence.company_id
                   and batch.id = occurrence.batch_id
                 where occurrence.tenant_id = ? and occurrence.company_id = ?
                   and occurrence.consolidation = 'IN_REVIEW'
                   and (?::uuid is null or batch.account_id = ?)
                """,
                Integer.class, scope.tenantId(), scope.companyId(), accountId, accountId);
        return count == null ? 0 : count;
    }

    private int countImported(AuthorizedScope scope, UUID accountId) {
        Integer count = jdbc.queryForObject(
                """
                select count(*) from actionfinance.statement_batch
                 where tenant_id = ? and company_id = ? and status = 'CONFIRMED'
                   and (?::uuid is null or account_id = ?)
                """,
                Integer.class,
                scope.tenantId(), scope.companyId(), accountId, accountId);
        return count == null ? 0 : count;
    }

    private LineView mapLine(java.sql.ResultSet rs) throws java.sql.SQLException {
        return new LineView(
                rs.getObject("id", UUID.class),
                rs.getObject("account_id", UUID.class),
                rs.getObject("batch_id", UUID.class),
                rs.getString("source_id"),
                rs.getString("record_type"),
                rs.getString("external_reference"),
                rs.getString("description"),
                rs.getObject("effective_on", LocalDate.class),
                rs.getString("direction"),
                rs.getString("event_kind"),
                rs.getString("balance_effect"),
                rs.getObject("gross_minor") == null ? null : rs.getLong("gross_minor"),
                rs.getBoolean("gross_absent"),
                rs.getObject("fee_minor") == null ? null : rs.getLong("fee_minor"),
                rs.getBoolean("fee_absent"),
                rs.getObject("net_minor") == null ? null : rs.getLong("net_minor"),
                rs.getBoolean("net_absent"),
                rs.getBoolean("currency_assumed"),
                rs.getString("classification_state"),
                rs.getString("initiative_state"),
                rs.getString("import_status"),
                rs.getInt("source_line_number"),
                List.of(),
                List.of());
    }

    private void requireSchema() {
        String name = jdbc.queryForObject("select to_regclass('actionfinance.statement_batch')", String.class);
        if (name == null) {
            throw new ResponseStatusException(HttpStatus.SERVICE_UNAVAILABLE, "Schema de extrato ausente. A operação não foi aceita.");
        }
    }

    private AuthorizedScope writable(ApplicationPrincipal principal, UUID companyId) {
        return access.requireWritable(principal, companyId, FinancePermissions.ACCOUNTS_WRITE);
    }

    private AuthorizedScope readable(ApplicationPrincipal principal, UUID companyId) {
        access.requirePermission(principal, companyId, FinancePermissions.ACCOUNTS_READ);
        return access.requireActiveMembership(principal, companyId);
    }

    private static String requireText(String value, int min, int max, String field, String message) {
        String text = value == null ? "" : value.trim();
        if (text.length() < min || text.length() > max) {
            throw new ValidationException(message, Map.of(field, message));
        }
        return text;
    }

    private static String selectionCanon(List<Integer> lineNumbers) {
        return lineNumbers.stream().sorted().map(String::valueOf).reduce((a, b) -> a + "," + b).orElse("");
    }

    private String json(Object value) {
        try {
            return mapper.writeValueAsString(value);
        } catch (JsonProcessingException exception) {
            throw new IllegalStateException(exception);
        }
    }

    private Map<String, Object> readJson(String json) {
        try {
            return mapper.readValue(json, new TypeReference<>() {});
        } catch (JsonProcessingException exception) {
            throw new IllegalStateException(exception);
        }
    }

    @Transactional(readOnly = true)
    public List<LinkView> links(ApplicationPrincipal principal, UUID companyId, UUID accountId) {
        AuthorizedScope scope = readable(principal, companyId);
        requireSchema();
        return jdbc.query(
                """
                select id, account_id, external_ref, provenance
                  from actionfinance.external_account_link
                 where tenant_id = ? and company_id = ? and (?::uuid is null or account_id = ?)
                 order by created_at
                """,
                (rs, n) -> new LinkView(rs.getObject("id", UUID.class), rs.getObject("account_id", UUID.class), rs.getString("external_ref"), rs.getString("provenance")),
                scope.tenantId(), scope.companyId(), accountId, accountId);
    }

    private static Object db(Object value, int sqlType) {
        return value == null ? new SqlParameterValue(sqlType, null) : value;
    }

    private static String sha256(String value) {
        return sha256(value.getBytes(StandardCharsets.UTF_8));
    }

    private static String sha256(byte[] value) {
        try {
            return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(value));
        } catch (NoSuchAlgorithmException exception) {
            throw new IllegalStateException(exception);
        }
    }

    public record LinkView(UUID id, UUID accountId, String externalRef, String provenance) {}

    public record PreviewView(
            UUID id,
            String previewToken,
            UUID accountId,
            String linkedRef,
            String profileId,
            boolean recognized,
            String fileDiagnostic,
            String blockReason,
            boolean confirmBlocked,
            boolean accountEvidenceRequired,
            boolean currencyAssumed,
            LocalDate periodFrom,
            LocalDate periodTo,
            List<StoredRow> rows,
            List<RowIssue> issues) {}

    public record ConfirmView(
            UUID batchId,
            int created,
            int enriched,
            int unchanged,
            int notImported,
            int preserved,
            int inReview,
            String partialTotalText,
            String accountAttestation) {}

    public record SuggestionView(UUID receiptId, String strength, String namespace, String reason, String divergence) {}

    public record LineView(
            UUID id,
            UUID accountId,
            UUID batchId,
            String sourceId,
            String recordType,
            String externalReference,
            String description,
            LocalDate effectiveOn,
            String direction,
            String eventKind,
            String balanceEffect,
            Long grossMinor,
            boolean grossAbsent,
            Long feeMinor,
            boolean feeAbsent,
            Long netMinor,
            boolean netAbsent,
            boolean currencyAssumed,
            String classificationState,
            String initiativeState,
            String importStatus,
            int sourceLineNumber,
            List<SuggestionView> suggestions,
            List<String> originalRows) {
        LineView withSuggestions(List<SuggestionView> suggestions) {
            return new LineView(id, accountId, batchId, sourceId, recordType, externalReference, description, effectiveOn, direction, eventKind, balanceEffect, grossMinor, grossAbsent, feeMinor, feeAbsent, netMinor, netAbsent, currencyAssumed, classificationState, initiativeState, importStatus, sourceLineNumber, suggestions, originalRows);
        }

        LineView withOriginal(List<String> originalRows) {
            return new LineView(id, accountId, batchId, sourceId, recordType, externalReference, description, effectiveOn, direction, eventKind, balanceEffect, grossMinor, grossAbsent, feeMinor, feeAbsent, netMinor, netAbsent, currencyAssumed, classificationState, initiativeState, importStatus, sourceLineNumber, suggestions, originalRows);
        }
    }

    public record StoredRow(
            int lineNumber,
            String rawText,
            boolean truncated,
            String eventKey,
            String contentHash,
            String sourceId,
            String recordType,
            String externalReference,
            String description,
            LocalDate effectiveOn,
            String direction,
            String eventKind,
            String balanceEffect,
            Long grossMinor,
            boolean grossAbsent,
            Long feeMinor,
            boolean feeAbsent,
            Long netMinor,
            boolean netAbsent,
            boolean currencyAssumed,
            String availability,
            boolean eligible) {
        static StoredRow from(ParsedRow row) {
            return new StoredRow(
                    row.lineNumber(), row.rawText(), row.truncated(), row.eventKey(), row.contentHash(), row.sourceId(), row.recordType(),
                    row.externalReference(), row.description(), row.effectiveOn(), row.direction(), row.eventKind(), row.balanceEffect(),
                    row.grossMinor(), row.grossAbsent(), row.feeMinor(), row.feeAbsent(), row.netMinor(), row.netAbsent(), row.currencyAssumed(), row.availability(), row.eligible());
        }

        StoredRow asIneligible() {
            return new StoredRow(lineNumber, rawText, truncated, eventKey, contentHash, sourceId, recordType, externalReference, description, effectiveOn, direction, eventKind, balanceEffect, grossMinor, grossAbsent, feeMinor, feeAbsent, netMinor, netAbsent, currencyAssumed, availability, false);
        }
    }

    private record LinkRow(String externalRef) {}

    private record Existing(
            UUID id,
            String contentHash,
            String externalReference,
            String description,
            LocalDate effectiveOn,
            String direction,
            Long grossMinor,
            Long feeMinor,
            Long netMinor) {}

    private record BatchRow(
            UUID previewId,
            UUID accountId,
            String status,
            String previewToken,
            String fileAccountRef,
            String previewJson,
            String selectionSha,
            String resultJson) {
        ConfirmView result() {
            try {
                return new ObjectMapper().readValue(resultJson, ConfirmView.class);
            } catch (JsonProcessingException exception) {
                throw new IllegalStateException(exception);
            }
        }
    }
}
