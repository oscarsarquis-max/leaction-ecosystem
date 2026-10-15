package br.com.actionfinance.application.finance;

import br.com.actionfinance.application.ApplicationPrincipal;
import br.com.actionfinance.application.DemoPrincipalCatalog;
import br.com.actionfinance.application.finance.FinanceExceptions.ValidationException;
import br.com.actionfinance.application.finance.PartyRecords.ImportBatchView;
import br.com.actionfinance.application.finance.PartyRecords.ImportReport;
import br.com.actionfinance.domain.CounterpartyRole;
import br.com.actionfinance.domain.DocumentNumbers;
import br.com.actionfinance.domain.PersonKind;
import br.com.actionfinance.domain.DocumentNumbers.NormalizedDocument;
import br.com.actionfinance.infrastructure.persistence.JdbcPartyRepository;
import br.com.actionfinance.infrastructure.persistence.JdbcPartyRepository.ImportBatchRow;
import br.com.actionfinance.infrastructure.persistence.JdbcPartyRepository.ImportLineRow;
import br.com.actionfinance.infrastructure.persistence.JdbcPartyRepository.PartyRow;
import br.com.actionfinance.interfaces.http.FinanceHttpModels.PartyImportConfirmRequest;
import br.com.actionfinance.interfaces.http.FinanceHttpModels.PartyImportLineDecision;
import br.com.actionfinance.interfaces.http.FinanceHttpModels.PartyImportPreviewRequest;
import br.com.actionfinance.interfaces.http.FinanceHttpModels.PartyWriteRequest;
import org.springframework.stereotype.Service;
import org.springframework.transaction.PlatformTransactionManager;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.transaction.support.TransactionTemplate;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.time.Clock;
import java.time.Instant;
import java.util.ArrayList;
import java.util.HexFormat;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.UUID;

@Service
public class PartyImportService {

    public static final String TEMPLATE =
            """
            nome;nome_fantasia;relacao;tipo_pessoa;pais_documento;tipo_documento;documento;situacao;unidade_nome;unidade_tipo;cep;logradouro;numero;sem_numero;complemento;bairro;municipio;uf;contato_nome;contato_funcao;contato_email;contato_telefone;fornecimento;categoria_fornecimento;observacao;origem_sistema;id_externo
            Padaria Modelo;;FORNECEDOR;JURIDICA;BR;CNPJ;12.ABC.345/01DE-35;ATIVO;Unidade central;LOJA;01001-000;Praça da Sé;100;NAO;;Sé;São Paulo;SP;Ana Souza;Compras;ana.modelo@example.test;1130000000;Farinha de trigo;Insumos;Dado sintético de modelo;FILE;ARQ-001
            João Produtor Rural;;FORNECEDOR;FISICA;BR;;;ATIVO;Sítio modelo;PRODUTOR_LOCAL;;;;;SIM;;;;SP;João Produtor;Produtor;;;;Leite in natura;Laticínio;Pessoa sem documento;FILE;ARQ-002
            """;

    private static final Map<String, String> DEFAULT_MAP = Map.ofEntries(
            Map.entry("name", "nome"),
            Map.entry("tradeName", "nome_fantasia"),
            Map.entry("role", "relacao"),
            Map.entry("personKind", "tipo_pessoa"),
            Map.entry("documentCountry", "pais_documento"),
            Map.entry("documentType", "tipo_documento"),
            Map.entry("documentNumber", "documento"),
            Map.entry("status", "situacao"),
            Map.entry("unitName", "unidade_nome"),
            Map.entry("unitKind", "unidade_tipo"),
            Map.entry("postalCode", "cep"),
            Map.entry("street", "logradouro"),
            Map.entry("number", "numero"),
            Map.entry("noNumber", "sem_numero"),
            Map.entry("complement", "complemento"),
            Map.entry("district", "bairro"),
            Map.entry("municipality", "municipio"),
            Map.entry("region", "uf"),
            Map.entry("contactName", "contato_nome"),
            Map.entry("contactRole", "contato_funcao"),
            Map.entry("contactEmail", "contato_email"),
            Map.entry("contactPhone", "contato_telefone"),
            Map.entry("supply", "fornecimento"),
            Map.entry("supplyCategory", "categoria_fornecimento"),
            Map.entry("notes", "observacao"),
            Map.entry("originSystem", "origem_sistema"),
            Map.entry("externalId", "id_externo"));

    private final CompanyAccessService access;
    private final JdbcPartyRepository parties;
    private final PartyDirectoryService directory;
    private final Clock clock;
    private final TransactionTemplate transactions;

    public PartyImportService(
            CompanyAccessService access,
            JdbcPartyRepository parties,
            PartyDirectoryService directory,
            Clock clock,
            PlatformTransactionManager transactionManager) {
        this.access = access;
        this.parties = parties;
        this.directory = directory;
        this.clock = clock;
        this.transactions = new TransactionTemplate(transactionManager);
    }

    @Transactional
    public ImportBatchView preview(ApplicationPrincipal principal, UUID companyId, PartyImportPreviewRequest body) {
        AuthorizedScope scope = access.requireWritable(principal, companyId, DemoPrincipalCatalog.PERMISSION_CATALOGS_WRITE);
        if (body == null || body.csvText() == null || body.csvText().isBlank()) {
            throw ValidationException.of("csvText", "Selecione um arquivo CSV.");
        }
        String filename = safeFilename(body.filename());
        if (filename.toLowerCase(Locale.ROOT).endsWith(".xlsx") || filename.toLowerCase(Locale.ROOT).endsWith(".xls")) {
            throw ValidationException.of("filename", "XLSX não é suportado neste recorte. Use o modelo CSV.");
        }
        String csv = body.csvText().replace("\uFEFF", "");
        String sha = sha256(csv);
        var existing = parties.findPreviewByHash(scope, sha);
        if (existing.isPresent()) {
            return parties.toView(existing.get(), parties.listLines(scope, existing.get().id()), null);
        }
        Map<String, String> columnMap = body.columnMap() == null || body.columnMap().isEmpty() ? DEFAULT_MAP : body.columnMap();
        List<Map<String, String>> rows = parseCsv(csv, columnMap);
        Instant now = Instant.now(clock);
        UUID batchId = UUID.randomUUID();
        ImportBatchRow batch = new ImportBatchRow(batchId, filename, sha, "PREVIEW", rows.size(), columnMap, now);
        parties.insertBatch(scope, batch, principal.actorId(), now);
        int lineNo = 1;
        for (Map<String, String> raw : rows) {
            Classified classified = classify(scope, raw);
            parties.insertLine(
                    scope,
                    new ImportLineRow(
                            UUID.randomUUID(),
                            batchId,
                            lineNo,
                            raw,
                            classified.classification(),
                            "NEW".equals(classified.classification()) && classified.error() == null,
                            classified.matchId(),
                            classified.previewVersion(),
                            null,
                            classified.error(),
                            batchId + ":" + sha + ":" + lineNo));
            lineNo++;
        }
        return parties.toView(batch, parties.listLines(scope, batchId), null);
    }

    public ImportBatchView confirm(ApplicationPrincipal principal, UUID companyId, UUID batchId, PartyImportConfirmRequest body) {
        AuthorizedScope scope = access.requireWritable(principal, companyId, DemoPrincipalCatalog.PERMISSION_CATALOGS_WRITE);
        Instant now = Instant.now(clock);
        ImportBatchRow batch = parties.findBatch(scope, batchId).orElseThrow(() -> new SecurityException("catalog-hidden"));
        List<ImportLineRow> lines = parties.listLines(scope, batchId);
        Map<UUID, PartyImportLineDecision> decisions = new LinkedHashMap<>();
        if (body != null && body.lines() != null) {
            for (PartyImportLineDecision decision : body.lines()) {
                decisions.put(decision.id(), decision);
            }
        }
        int created = 0;
        int updated = 0;
        int skipped = 0;
        int rejected = 0;
        boolean needsReview = false;
        for (ImportLineRow line : lines) {
            if (line.result() != null) {
                switch (line.result()) {
                    case "CREATED" -> created++;
                    case "UPDATED" -> updated++;
                    case "SKIPPED" -> skipped++;
                    default -> rejected++;
                }
                continue;
            }
            PartyImportLineDecision decision = decisions.get(line.id());
            boolean selected = decision != null ? decision.selected() : line.selected();
            String resolution = decision == null ? "CREATE" : decision.resolution();
            if (!selected || "INVALID".equals(line.classification())) {
                parties.updateLineResult(scope, line.id(), false, "SKIPPED", line.errorMessage());
                skipped++;
                continue;
            }
            Classified current = classify(scope, line.raw());
            if ("CONFLICT".equals(current.classification())
                    || (line.previewVersion() != null
                            && current.previewVersion() != null
                            && !line.previewVersion().equals(current.previewVersion()))) {
                parties.updateLineResult(
                        scope,
                        line.id(),
                        true,
                        "REJECTED",
                        "O cadastro mudou desde a prévia. Reveja esta linha.");
                rejected++;
                needsReview = true;
                continue;
            }
            try {
                String outcome = transactions.execute(status -> applyLine(principal, companyId, line, current, resolution, now));
                if ("CREATED".equals(outcome)) {
                    created++;
                } else if ("UPDATED".equals(outcome)) {
                    updated++;
                } else {
                    skipped++;
                }
            } catch (RuntimeException ex) {
                parties.updateLineResult(scope, line.id(), true, "REJECTED", clipError(ex.getMessage()));
                rejected++;
            }
        }
        parties.markBatchConfirmed(scope, batchId, now, principal.actorId());
        ImportReport report = new ImportReport(
                created,
                updated,
                skipped,
                rejected,
                created + updated + skipped + rejected != lines.size() || rejected > 0 || skipped > 0 && created + updated > 0,
                needsReview
                        ? "Processamento por linha concluído com revisão pendente. Não houve sucesso total."
                        : summary(created, updated, skipped, rejected, lines.size()));
        return parties.toView(parties.findBatch(scope, batchId).orElse(batch), parties.listLines(scope, batchId), report);
    }

    public ImportBatchView get(ApplicationPrincipal principal, UUID companyId, UUID batchId) {
        AuthorizedScope scope = access.requireWritable(principal, companyId, DemoPrincipalCatalog.PERMISSION_CATALOGS_WRITE);
        ImportBatchRow batch = parties.findBatch(scope, batchId).orElseThrow(() -> new SecurityException("catalog-hidden"));
        return parties.toView(batch, parties.listLines(scope, batchId), null);
    }

    private String applyLine(
            ApplicationPrincipal principal,
            UUID companyId,
            ImportLineRow line,
            Classified classified,
            String resolution,
            Instant now) {
        AuthorizedScope scope = new AuthorizedScope(
                access.requireReadable(principal, companyId).tenantId(), companyId);
        if ("SKIP".equalsIgnoreCase(resolution) || "OPEN".equalsIgnoreCase(resolution)) {
            parties.updateLineResult(scope, line.id(), true, "SKIPPED", null);
            return "SKIPPED";
        }
        PartyWriteRequest request = toWrite(line.raw(), classified, resolution);
        if (classified.matchId() != null && ("ENRICH".equalsIgnoreCase(resolution) || "APPLY_NON_EMPTY".equalsIgnoreCase(resolution))) {
            PartyRow current = parties.lock(scope, classified.matchId()).orElseThrow();
            directory.update(principal, companyId, classified.matchId(), withVersion(request, current.version(), current));
            parties.updateLineResult(scope, line.id(), true, "UPDATED", null);
            return "UPDATED";
        }
        directory.create(principal, companyId, request);
        parties.updateLineResult(scope, line.id(), true, "CREATED", null);
        return "CREATED";
    }

    private PartyWriteRequest withVersion(PartyWriteRequest request, long version, PartyRow current) {
        return new PartyWriteRequest(
                first(request.name(), current.name()),
                first(request.tradeName(), current.tradeName()),
                request.personKind(),
                request.role(),
                request.customer(),
                request.supplier(),
                request.active(),
                current.documentPending() ? request.documentCountry() : current.documentCountry(),
                current.documentPending() ? request.documentType() : (current.documentType() == null ? null : current.documentType().name()),
                current.documentPending() ? request.documentNumber() : current.documentNumber(),
                current.originKind().name(),
                first(request.notes(), current.notes()),
                version,
                request.units(),
                request.addresses(),
                request.contacts(),
                request.supplies(),
                request.externalIdentities());
    }

    private Classified classify(AuthorizedScope scope, Map<String, String> raw) {
        String name = raw.getOrDefault("name", "").trim();
        CounterpartyRole role = parseRole(raw.get("role"));
        if (name.isEmpty() || role == null) {
            return new Classified("INVALID", null, null, "Nome e relação são obrigatórios.");
        }
        PersonKind personKind = switch (raw.getOrDefault("personKind", "").trim().toUpperCase(Locale.ROOT)) {
            case "JURIDICA", "LEGAL" -> PersonKind.LEGAL;
            case "FISICA", "NATURAL" -> PersonKind.NATURAL;
            default -> PersonKind.UNSPECIFIED;
        };
        NormalizedDocument document = null;
        try {
            document = DocumentNumbers.parse(
                    raw.get("documentCountry"), raw.get("documentType"), raw.get("documentNumber"), personKind);
        } catch (ValidationException ex) {
            return new Classified("INVALID", null, null, ex.getMessage());
        }
        if (document != null) {
            var existing = parties.findByDocument(scope, document.country(), document.type(), document.normalized(), null);
            if (existing.isPresent()) {
                PartyRow row = existing.get();
                boolean conflict = !row.name().equalsIgnoreCase(name) || row.role() != role;
                return new Classified(
                        conflict ? "CONFLICT" : "DUPLICATE",
                        row.id(),
                        row.version(),
                        conflict ? "Documento igual a cadastro existente com dados diferentes." : null);
            }
            var claim = parties.findDocumentClaimOwner(scope, document.country(), document.type(), document.normalized(), null);
            if (claim.isPresent()) {
                return new Classified("CONFLICT", claim.get(), null, "Documento já reivindica outro cadastro nesta empresa.");
            }
        }
        var names = parties.findNameCandidates(scope, name, null);
        if (!names.isEmpty() && document == null) {
            return new Classified(
                    "DUPLICATE",
                    names.getFirst().id(),
                    null,
                    "Nome semelhante. Homonímia exige revisão explícita; não funde automaticamente.");
        }
        return new Classified("NEW", null, null, null);
    }

    private static PartyWriteRequest toWrite(Map<String, String> raw, Classified classified, String resolution) {
        CounterpartyRole role = parseRole(raw.get("role"));
        boolean customer = role == CounterpartyRole.CUSTOMER || role == CounterpartyRole.BOTH;
        boolean supplier = role == CounterpartyRole.SUPPLIER || role == CounterpartyRole.BOTH;
        String person = switch (raw.getOrDefault("personKind", "").trim().toUpperCase(Locale.ROOT)) {
            case "JURIDICA", "LEGAL" -> "LEGAL";
            case "FISICA", "NATURAL" -> "NATURAL";
            default -> "UNSPECIFIED";
        };
        boolean active = !"INATIVO".equalsIgnoreCase(raw.getOrDefault("status", "ATIVO"));
        boolean noNumber = truthy(raw.get("noNumber"));
        return new PartyWriteRequest(
                raw.get("name"),
                emptyToNull(raw.get("tradeName")),
                person,
                role == null ? "CUSTOMER" : role.name(),
                customer,
                supplier,
                active,
                emptyToNull(raw.get("documentCountry")),
                normalizeDocType(raw.get("documentType")),
                emptyToNull(raw.get("documentNumber")),
                "FILE",
                emptyToNull(raw.get("notes")),
                null,
                emptyToNull(raw.get("unitName")) == null
                        ? List.of()
                        : List.of(new br.com.actionfinance.interfaces.http.FinanceHttpModels.PartyUnitWrite(
                                null,
                                raw.get("unitName"),
                                mapUnit(raw.get("unitKind")),
                                true,
                                true,
                                null,
                                null,
                                null)),
                emptyToNull(raw.get("street")) == null && emptyToNull(raw.get("municipality")) == null
                        ? List.of()
                        : List.of(new br.com.actionfinance.interfaces.http.FinanceHttpModels.PartyAddressWrite(
                                null,
                                null,
                                first(raw.get("documentCountry"), "BR"),
                                emptyToNull(raw.get("postalCode")),
                                emptyToNull(raw.get("street")),
                                noNumber ? null : emptyToNull(raw.get("number")),
                                noNumber,
                                emptyToNull(raw.get("complement")),
                                emptyToNull(raw.get("district")),
                                emptyToNull(raw.get("municipality")),
                                emptyToNull(raw.get("region")),
                                "MAIN",
                                true)),
                emptyToNull(raw.get("contactName")) == null
                        ? List.of()
                        : List.of(new br.com.actionfinance.interfaces.http.FinanceHttpModels.PartyContactWrite(
                                null,
                                raw.get("contactName"),
                                emptyToNull(raw.get("contactRole")),
                                emptyToNull(raw.get("contactEmail")),
                                emptyToNull(raw.get("contactPhone")),
                                true,
                                true)),
                emptyToNull(raw.get("supply")) == null
                        ? List.of()
                        : List.of(new br.com.actionfinance.interfaces.http.FinanceHttpModels.PartySupplyWrite(
                                null,
                                raw.get("supply"),
                                emptyToNull(raw.get("supplyCategory")),
                                null,
                                true)),
                emptyToNull(raw.get("externalId")) == null
                        ? List.of()
                        : List.of(new br.com.actionfinance.interfaces.http.FinanceHttpModels.PartyExternalWrite(
                                first(raw.get("originSystem"), "FILE"),
                                null,
                                raw.get("externalId"),
                                null)));
    }

    private static List<Map<String, String>> parseCsv(String csv, Map<String, String> columnMap) {
        String[] lines = csv.split("\\r?\\n");
        if (lines.length < 2) {
            throw ValidationException.of("csvText", "O arquivo precisa de cabeçalho e ao menos uma linha.");
        }
        char separator = lines[0].contains(";") && !lines[0].contains(",") ? ';' : ',';
        List<String> headers = splitRow(lines[0], separator).stream().map(header -> header.trim().toLowerCase(Locale.ROOT)).toList();
        Map<String, Integer> index = new LinkedHashMap<>();
        for (int i = 0; i < headers.size(); i++) {
            index.put(headers.get(i), i);
        }
        List<Map<String, String>> rows = new ArrayList<>();
        for (int i = 1; i < lines.length; i++) {
            if (lines[i].isBlank()) {
                continue;
            }
            List<String> cells = splitRow(lines[i], separator);
            Map<String, String> raw = new LinkedHashMap<>();
            for (Map.Entry<String, String> entry : columnMap.entrySet()) {
                Integer at = index.get(entry.getValue().trim().toLowerCase(Locale.ROOT));
                raw.put(entry.getKey(), at == null || at >= cells.size() ? "" : cells.get(at).trim());
            }
            rows.add(raw);
        }
        return rows;
    }

    private static List<String> splitRow(String line, char separator) {
        List<String> cells = new ArrayList<>();
        StringBuilder current = new StringBuilder();
        boolean quoted = false;
        for (int i = 0; i < line.length(); i++) {
            char ch = line.charAt(i);
            if (ch == '"') {
                quoted = !quoted;
            } else if (ch == separator && !quoted) {
                cells.add(current.toString());
                current.setLength(0);
            } else {
                current.append(ch);
            }
        }
        cells.add(current.toString());
        return cells;
    }

    private static CounterpartyRole parseRole(String raw) {
        if (raw == null) {
            return null;
        }
        return switch (raw.trim().toUpperCase(Locale.ROOT)) {
            case "CLIENTE", "CUSTOMER" -> CounterpartyRole.CUSTOMER;
            case "FORNECEDOR", "SUPPLIER" -> CounterpartyRole.SUPPLIER;
            case "AMBOS", "BOTH" -> CounterpartyRole.BOTH;
            default -> null;
        };
    }

    private static String normalizeDocType(String raw) {
        if (raw == null || raw.isBlank()) {
            return null;
        }
        return switch (raw.trim().toUpperCase(Locale.ROOT)) {
            case "CNPJ" -> "CNPJ";
            case "CPF" -> "CPF";
            default -> "OTHER";
        };
    }

    private static String mapUnit(String raw) {
        if (raw == null) {
            return "OTHER";
        }
        return switch (raw.trim().toUpperCase(Locale.ROOT)) {
            case "LOJA", "STORE" -> "STORE";
            case "DEPOSITO", "DEPOT" -> "DEPOT";
            case "ARMAZEM", "WAREHOUSE" -> "WAREHOUSE";
            case "PRODUTOR_LOCAL", "LOCAL_PRODUCER" -> "LOCAL_PRODUCER";
            case "ESCRITORIO", "OFFICE" -> "OFFICE";
            default -> "OTHER";
        };
    }

    private static boolean truthy(String raw) {
        if (raw == null) {
            return false;
        }
        return raw.equalsIgnoreCase("SIM") || raw.equalsIgnoreCase("TRUE") || raw.equalsIgnoreCase("1");
    }

    private static String first(String preferred, String fallback) {
        String value = emptyToNull(preferred);
        return value == null ? fallback : value;
    }

    private static String emptyToNull(String value) {
        return value == null || value.isBlank() ? null : value.trim();
    }

    private static String safeFilename(String filename) {
        if (filename == null || filename.isBlank()) {
            return "cadastros.csv";
        }
        String name = filename.replace("\\", "/");
        int slash = name.lastIndexOf('/');
        return slash >= 0 ? name.substring(slash + 1) : name;
    }

    private static String sha256(String csv) {
        try {
            byte[] digest = MessageDigest.getInstance("SHA-256").digest(csv.getBytes(StandardCharsets.UTF_8));
            return HexFormat.of().formatHex(digest);
        } catch (NoSuchAlgorithmException ex) {
            throw new IllegalStateException(ex);
        }
    }

    private static String clipError(String message) {
        if (message == null) {
            return "Linha rejeitada.";
        }
        return message.length() > 400 ? message.substring(0, 400) : message;
    }

    private static String summary(int created, int updated, int skipped, int rejected, int total) {
        if (rejected == 0 && skipped == 0 && created + updated == total) {
            return "Todas as linhas selecionadas foram gravadas.";
        }
        return "Processamento por linha: %d criados, %d atualizados, %d ignorados, %d rejeitados."
                .formatted(created, updated, skipped, rejected);
    }

    private record Classified(String classification, UUID matchId, Long previewVersion, String error) {}
}
