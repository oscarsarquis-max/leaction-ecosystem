import { useEffect, useMemo, useRef, useState, type FormEvent } from "react";
import { Link, useSearchParams } from "react-router-dom";
import {
  FISCAL_ENTRY_OPTIONS,
  NFE_PUBLIC_CONSULT_URL,
  accessKeyDigits,
  isCompleteAccessKey,
  isFiscalEntryOption,
} from "../language/fiscal";
import { useCommand } from "../ops/useCommand";
import { canCaptureFiscalDocument } from "../session/fiscalAccess";
import { useOrganization } from "../session/OrganizationContext";

type Line = {
  description: string;
  unit_code: string;
  quantity: string;
  unit_price: string;
};

type FieldErrors = Partial<Record<string, string>>;
type EntryMode = "manual" | "xml";

const EMPTY_LINE: Line = { description: "", unit_code: "KG", quantity: "", unit_price: "" };
const READ_FAILED = "Não foi possível ler o arquivo escolhido.";

function readAsText(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onerror = () => reject(new Error(READ_FAILED));
    reader.onload = () => resolve(String(reader.result ?? ""));
    reader.readAsText(file);
  });
}

function readAsDataUrl(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onerror = () => reject(new Error(READ_FAILED));
    reader.onload = () => resolve(String(reader.result ?? ""));
    reader.readAsDataURL(file);
  });
}

function fileKindAllowed(file: File): boolean {
  return file.type.startsWith("image/") || file.type === "application/pdf" || /\.pdf$/i.test(file.name);
}

function lineTotal(line: Line): number | null {
  const qty = Number(line.quantity.replace(",", "."));
  const price = Number(line.unit_price.replace(",", "."));
  if (!Number.isFinite(qty) || !Number.isFinite(price) || line.unit_price.trim() === "") return null;
  return qty * price;
}

export function FiscalEntryNewPage() {
  const { api, hasPermission } = useOrganization();
  const command = useCommand();
  const [params] = useSearchParams();
  const requested = params.get("origem");
  const highlighted = isFiscalEntryOption(requested) ? requested : null;

  const [mode, setMode] = useState<EntryMode>(highlighted === "xml" ? "xml" : "manual");
  const [accessKey, setAccessKey] = useState("");
  const [supplierName, setSupplierName] = useState("");
  const [supplierTaxId, setSupplierTaxId] = useState("");
  const [documentNumber, setDocumentNumber] = useState("");
  const [series, setSeries] = useState("");
  const [issuedOn, setIssuedOn] = useState("");
  const [lines, setLines] = useState<Line[]>([{ ...EMPTY_LINE }]);
  const [reviewing, setReviewing] = useState(false);
  const [fieldErrors, setFieldErrors] = useState<FieldErrors>({});
  const [xmlFile, setXmlFile] = useState<File | null>(null);
  const [refFile, setRefFile] = useState<File | null>(null);
  const [keepFile, setKeepFile] = useState(false);
  const [readError, setReadError] = useState<string | null>(null);
  const [savedId, setSavedId] = useState<string | null>(null);
  const [savedLabel, setSavedLabel] = useState("");
  const [attachedName, setAttachedName] = useState<string | null>(null);

  const requestedRef = useRef<HTMLInputElement | null>(null);
  useEffect(() => {
    if (highlighted) requestedRef.current?.focus();
  }, [highlighted]);

  const allowed = canCaptureFiscalDocument(hasPermission);
  const busy = !allowed || command.pending;
  const keyDigits = accessKeyDigits(accessKey);
  const publicConsultReady = isCompleteAccessKey(accessKey);
  const usableLines = lines.filter((line) => line.description.trim() && line.quantity.trim());
  const reviewTotal = useMemo(() => {
    const totals = usableLines.map(lineTotal);
    if (totals.some((value) => value == null)) return null;
    return totals.reduce((sum, value) => (sum ?? 0) + (value ?? 0), 0);
  }, [usableLines]);

  function validateManual(): FieldErrors {
    const errors: FieldErrors = {};
    if (keyDigits && keyDigits.length !== 44) {
      errors.access_key = "A chave de acesso tem 44 dígitos. Sem chave, preencha os dados da nota.";
    }
    if (!supplierName.trim()) errors.supplier_name = "Informe o fornecedor.";
    if (!documentNumber.trim()) errors.document_number = "Informe o número da nota.";
    if (!usableLines.length) errors.items = "Informe ao menos um item com descrição e quantidade.";
    return errors;
  }

  async function attachReference(documentId: string, file: File) {
    if (!fileKindAllowed(file)) {
      setReadError("Só foto ou PDF podem ser guardados como referência.");
      return;
    }
    const content = await readAsDataUrl(file);
    await command.run(`fiscal-ref:${documentId}:${file.name}:${file.size}`, (key) =>
      api.attachFiscalScan({ document_id: documentId, filename: file.name, content }, key),
    );
    setAttachedName(`${file.name} · ${(file.size / 1024).toFixed(0)} KB`);
  }

  async function submitManual(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (busy || savedId) return;
    setReadError(null);
    const errors = validateManual();
    setFieldErrors(errors);
    if (Object.keys(errors).length) {
      setReviewing(false);
      return;
    }
    if (!reviewing) {
      setReviewing(true);
      return;
    }
    const created = await command.run(`fiscal-manual:${documentNumber.trim()}:${accessKey.trim()}`, (key) =>
      api.createManualFiscal(
        {
          supplier_name: supplierName.trim(),
          supplier_tax_id: supplierTaxId.replace(/\D/g, "") || null,
          access_key: keyDigits || null,
          document_number: documentNumber.trim(),
          series: series.trim() || null,
          issued_on: issuedOn || null,
          items: usableLines.map((line) => ({
            description: line.description.trim(),
            unit_code: line.unit_code.trim() || null,
            quantity: line.quantity.trim(),
            unit_price: line.unit_price.trim() || null,
          })),
        },
        key,
      ),
    );
    const id = created?.data?.id;
    if (!id) return;
    setSavedId(id);
    setSavedLabel(`Nota ${documentNumber.trim()}${series.trim() ? ` · série ${series.trim()}` : ""}`);
    if (keepFile && refFile) {
      try {
        await attachReference(id, refFile);
      } catch (error) {
        if (error instanceof Error && error.message === READ_FAILED) setReadError(error.message);
        else setReadError("A nota foi gravada. O arquivo de referência não pôde ser guardado.");
      }
    }
  }

  async function submitXml(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (busy || !xmlFile || savedId) return;
    setReadError(null);
    try {
      const content = await readAsText(xmlFile);
      const created = await command.run(`fiscal-xml:${xmlFile.name}:${xmlFile.size}`, (key) =>
        api.importFiscalXml({ filename: xmlFile.name, content }, key),
      );
      const id = created?.data?.id;
      if (!id) return;
      setSavedId(id);
      setSavedLabel(xmlFile.name);
    } catch (error) {
      if (error instanceof Error && error.message === READ_FAILED) setReadError(error.message);
    }
  }

  async function submitLateAttachment(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!savedId || !refFile || busy) return;
    setReadError(null);
    try {
      await attachReference(savedId, refFile);
    } catch (error) {
      if (error instanceof Error && error.message === READ_FAILED) setReadError(error.message);
      else setReadError("A nota permanece gravada. O arquivo de referência não pôde ser guardado.");
    }
  }

  const xml = FISCAL_ENTRY_OPTIONS.find((row) => row.slug === "xml")!;

  return (
    <div className="entry-page">
      <header className="page-head">
        <h1>Registrar entrada</h1>
      </header>
      <p className="lede">
        Informe a chave e os dados da nota, ou importe o XML. Foto ou PDF, se você quiser guardar,
        não são lidos e não validam a nota. O estoque só muda depois, numa confirmação separada.
      </p>

      {!allowed ? (
        <p className="meta" role="status">
          Seu papel permite acompanhar as entradas, mas não registrar novas. Fale com quem cuida de
          compras.
        </p>
      ) : null}

      {command.error ? (
        <p className="error" role="alert">
          {command.error.message || "Não foi possível abrir a entrada."}
        </p>
      ) : null}
      {readError ? (
        <p className="error" role="alert">
          {readError}
        </p>
      ) : null}

      {savedId ? (
        <section className="card entry-success" aria-label="Nota gravada">
          <p role="status">
            <strong>Nota gravada · estoque pendente.</strong> {savedLabel} foi salva com os itens
            informados. O estoque ainda não mudou.
          </p>
          <p>
            <Link className="primary" to={`/gestao/compras/entradas/${savedId}`}>
              Revisar e confirmar entrada no estoque
            </Link>
          </p>
          {attachedName ? (
            <p className="meta" role="status">
              Referência guardada: {attachedName}. O arquivo não foi lido nem validou a nota.
            </p>
          ) : (
            <form className="entry-group entry-group--secondary" onSubmit={submitLateAttachment}>
              <h2>Guardar foto ou PDF como referência</h2>
              <p className="meta">O arquivo não é lido nem valida a nota. Você pode concluir sem anexá-lo.</p>
              <label>
                Arquivo de referência
                <input
                  type="file"
                  accept="image/*,application/pdf"
                  disabled={busy}
                  onChange={(event) => setRefFile(event.target.files?.[0] ?? null)}
                />
              </label>
              <button type="submit" className="ghost" disabled={busy || !refFile}>
                Guardar referência
              </button>
            </form>
          )}
          <p>
            <button
              type="button"
              className="ghost"
              onClick={() => {
                setSavedId(null);
                setSavedLabel("");
                setAttachedName(null);
                setReviewing(false);
                setRefFile(null);
                setKeepFile(false);
                setXmlFile(null);
              }}
            >
              Registrar outra entrada
            </button>
          </p>
        </section>
      ) : (
        <>
          <fieldset className="entry-mode">
            <legend>Como registrar</legend>
            <label className="entry-check">
              <input
                type="radio"
                name="entrada-modo"
                checked={mode === "manual"}
                disabled={busy}
                onChange={() => setMode("manual")}
              />
              Preencher nota
            </label>
            <label className="entry-check">
              <input
                type="radio"
                name="entrada-modo"
                checked={mode === "xml"}
                disabled={busy}
                onChange={() => setMode("xml")}
              />
              Importar XML
            </label>
          </fieldset>

          {mode === "manual" ? (
            <section
              className={highlighted === "manual" ? "card entry-option is-highlighted" : "card entry-option"}
              aria-label="Preencher nota"
            >
              <h2>Preencher nota</h2>
              <p>
                A chave digitada identifica o documento informado. Sem consulta oficial bem-sucedida,
                ela não aparece como nota validada.
              </p>
              <form className="entry-form" onSubmit={submitManual}>
                <fieldset className="entry-group">
                  <legend>Documento</legend>
                  <div className="entry-field">
                    <label htmlFor="entrada-chave">Chave de acesso</label>
                    <input
                      id="entrada-chave"
                      ref={highlighted === "manual" ? requestedRef : undefined}
                      value={accessKey}
                      inputMode="numeric"
                      autoComplete="off"
                      disabled={busy}
                      aria-invalid={fieldErrors.access_key ? true : undefined}
                      aria-describedby={fieldErrors.access_key ? "entrada-chave-erro" : undefined}
                      onChange={(event) => {
                        setAccessKey(event.target.value);
                        setReviewing(false);
                      }}
                    />
                    {fieldErrors.access_key ? (
                      <span id="entrada-chave-erro" className="error" role="alert">
                        {fieldErrors.access_key}
                      </span>
                    ) : publicConsultReady ? (
                      <p className="meta">
                        <a href={NFE_PUBLIC_CONSULT_URL} target="_blank" rel="noopener noreferrer">
                          Consultar esta chave no portal da Fazenda
                        </a>
                        . Você conclui a verificação humana no site oficial. Abrir o portal não valida a
                        nota na Panne.
                      </p>
                    ) : (
                      <p className="meta">
                        A chave tem 44 dígitos, como no código de barras do DANFE.
                        {keyDigits.length ? ` Informados: ${keyDigits.length}.` : ""} Sem consulta oficial
                        bem-sucedida, ela não valida a nota.
                      </p>
                    )}
                  </div>
                  <div className="entry-doc-row">
                    <div className="entry-field">
                      <label htmlFor="entrada-numero">Número da nota</label>
                      <input
                        id="entrada-numero"
                        value={documentNumber}
                        inputMode="numeric"
                        autoComplete="off"
                        disabled={busy}
                        aria-invalid={fieldErrors.document_number ? true : undefined}
                        aria-describedby={fieldErrors.document_number ? "entrada-numero-erro" : undefined}
                        onChange={(event) => {
                          setDocumentNumber(event.target.value);
                          setReviewing(false);
                        }}
                      />
                      {fieldErrors.document_number ? (
                        <span id="entrada-numero-erro" className="error" role="alert">
                          {fieldErrors.document_number}
                        </span>
                      ) : null}
                    </div>
                    <div className="entry-field">
                      <label htmlFor="entrada-serie">Série</label>
                      <input
                        id="entrada-serie"
                        value={series}
                        autoComplete="off"
                        disabled={busy}
                        onChange={(event) => {
                          setSeries(event.target.value);
                          setReviewing(false);
                        }}
                      />
                    </div>
                    <div className="entry-field">
                      <label htmlFor="entrada-emissao">Data de emissão</label>
                      <input
                        id="entrada-emissao"
                        type="date"
                        value={issuedOn}
                        disabled={busy}
                        onChange={(event) => {
                          setIssuedOn(event.target.value);
                          setReviewing(false);
                        }}
                      />
                    </div>
                  </div>
                </fieldset>

                <fieldset className="entry-group">
                  <legend>Fornecedor</legend>
                  <label htmlFor="entrada-fornecedor">Fornecedor</label>
                  <input
                    id="entrada-fornecedor"
                    value={supplierName}
                    autoComplete="off"
                    disabled={busy}
                    aria-invalid={fieldErrors.supplier_name ? true : undefined}
                    aria-describedby={fieldErrors.supplier_name ? "entrada-fornecedor-erro" : undefined}
                    onChange={(event) => {
                      setSupplierName(event.target.value);
                      setReviewing(false);
                    }}
                  />
                  {fieldErrors.supplier_name ? (
                    <span id="entrada-fornecedor-erro" className="error" role="alert">
                      {fieldErrors.supplier_name}
                    </span>
                  ) : null}
                  <label>
                    CNPJ do fornecedor
                    <input
                      value={supplierTaxId}
                      inputMode="numeric"
                      autoComplete="off"
                      disabled={busy}
                      onChange={(event) => setSupplierTaxId(event.target.value)}
                    />
                  </label>
                </fieldset>

                <fieldset className="entry-group">
                  <legend>Itens</legend>
                  {lines.map((line, index) => (
                    <div className="entry-item" key={index}>
                      <label>
                        Descrição
                        <input
                          value={line.description}
                          autoComplete="off"
                          disabled={busy}
                          onChange={(event) => {
                            const next = [...lines];
                            next[index] = { ...line, description: event.target.value };
                            setLines(next);
                            setReviewing(false);
                          }}
                        />
                      </label>
                      <label>
                        Quantidade
                        <input
                          value={line.quantity}
                          inputMode="decimal"
                          autoComplete="off"
                          disabled={busy}
                          onChange={(event) => {
                            const next = [...lines];
                            next[index] = { ...line, quantity: event.target.value };
                            setLines(next);
                            setReviewing(false);
                          }}
                        />
                      </label>
                      <label>
                        Unidade
                        <input
                          value={line.unit_code}
                          autoComplete="off"
                          disabled={busy}
                          onChange={(event) => {
                            const next = [...lines];
                            next[index] = { ...line, unit_code: event.target.value };
                            setLines(next);
                            setReviewing(false);
                          }}
                        />
                      </label>
                      <label>
                        Valor unitário
                        <input
                          value={line.unit_price}
                          inputMode="decimal"
                          autoComplete="off"
                          disabled={busy}
                          onChange={(event) => {
                            const next = [...lines];
                            next[index] = { ...line, unit_price: event.target.value };
                            setLines(next);
                          }}
                        />
                      </label>
                    </div>
                  ))}
                  {fieldErrors.items ? (
                    <span className="error" role="alert">
                      {fieldErrors.items}
                    </span>
                  ) : null}
                  <button
                    type="button"
                    className="ghost"
                    disabled={busy}
                    onClick={() => setLines((current) => [...current, { ...EMPTY_LINE }])}
                  >
                    Acrescentar item
                  </button>
                </fieldset>

                <fieldset
                  className={
                    highlighted === "foto"
                      ? "entry-group entry-group--secondary is-highlighted"
                      : "entry-group entry-group--secondary"
                  }
                >
                  <h2>Guardar foto ou PDF como referência</h2>
                  <p className="meta">
                    O arquivo não é lido nem valida a nota. Você pode concluir sem anexá-lo.
                  </p>
                  <label className="entry-check">
                    <input
                      type="checkbox"
                      checked={keepFile}
                      disabled={busy}
                      onChange={(event) => {
                        setKeepFile(event.target.checked);
                        if (!event.target.checked) setRefFile(null);
                      }}
                    />
                    Quero guardar o arquivo com esta nota
                  </label>
                  {keepFile ? (
                    <label>
                      Arquivo de referência
                      <input
                        type="file"
                        accept="image/*,application/pdf"
                        disabled={busy}
                        onChange={(event) => setRefFile(event.target.files?.[0] ?? null)}
                      />
                    </label>
                  ) : null}
                  {keepFile && refFile ? (
                    <p className="meta" role="status">
                      Anexo escolhido: {refFile.name} · {(refFile.size / 1024).toFixed(0)} KB. Nada foi
                      extraído deste arquivo.
                    </p>
                  ) : null}
                </fieldset>

                {reviewing ? (
                  <section className="entry-review" aria-label="Revisão">
                    <h3>Revisão</h3>
                    <p>Fornecedor: {supplierName.trim()}</p>
                    <p>
                      Nota {documentNumber.trim()}
                      {series.trim() ? ` · série ${series.trim()}` : ""}
                      {issuedOn ? ` · ${issuedOn}` : ""}
                    </p>
                    {keyDigits ? (
                      <p>
                        Chave informada
                        {publicConsultReady ? ", ainda sem consulta oficial bem-sucedida" : ""}. Abrir o
                        portal não valida a nota na Panne.
                      </p>
                    ) : null}
                    <ul>
                      {usableLines.map((line) => (
                        <li key={`${line.description}-${line.quantity}`}>
                          {line.description} · {line.quantity} {line.unit_code}
                          {line.unit_price.trim() ? ` · R$ ${line.unit_price}` : ""}
                        </li>
                      ))}
                    </ul>
                    {reviewTotal != null ? <p>Total informado: R$ {reviewTotal.toFixed(2)}</p> : null}
                    <p className="meta">
                      Gravar a nota não lança estoque. A confirmação de entrada continua numa ação
                      seguinte.
                    </p>
                  </section>
                ) : null}

                <button type="submit" className="primary manual-primary" disabled={busy}>
                  {reviewing ? "Gravar nota" : "Revisar e gravar"}
                </button>
              </form>
            </section>
          ) : (
            <section
              className={highlighted === "xml" ? "card entry-option is-highlighted" : "card entry-option"}
              aria-label={xml.title}
            >
              <h2>{xml.title}</h2>
              <p>{xml.summary}</p>
              <form onSubmit={submitXml}>
                <label>
                  Arquivo XML da nota
                  <input
                    ref={highlighted === "xml" ? requestedRef : undefined}
                    type="file"
                    accept=".xml,text/xml,application/xml"
                    onChange={(event) => setXmlFile(event.target.files?.[0] ?? null)}
                    disabled={busy}
                  />
                </label>
                <button type="submit" className="primary" disabled={busy || !xmlFile}>
                  {xml.action}
                </button>
              </form>
            </section>
          )}

          <section className="card entry-option entry-option--muted" aria-label="Buscar documentos da Fazenda">
            <h2>Buscar documentos da Fazenda</h2>
            <p className="meta" role="status">
              A busca automática com certificado continua desativada e não cria nota. Depois de
              informar a chave, a consulta pública é no portal da Fazenda, com a verificação humana
              de lá. Isso não lê foto nem PDF e não confirma estoque.
            </p>
          </section>
        </>
      )}

      <p>
        <Link className="ghost" to="/gestao/compras/entradas">
          Voltar às entradas fiscais
        </Link>
      </p>
    </div>
  );
}
