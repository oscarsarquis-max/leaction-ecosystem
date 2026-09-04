import { useEffect, useRef, useState, type FormEvent } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import type { Envelope, FiscalDocument } from "../api/types";
import { FISCAL_ENTRY_OPTIONS, isFiscalEntryOption } from "../language/fiscal";
import { useCommand } from "../ops/useCommand";
import { canCaptureFiscalDocument } from "../session/fiscalAccess";
import { useOrganization } from "../session/OrganizationContext";

type ManualForm = {
  supplier_name: string;
  supplier_tax_id: string;
  document_number: string;
  series: string;
  issued_on: string;
};

const EMPTY_MANUAL: ManualForm = {
  supplier_name: "",
  supplier_tax_id: "",
  document_number: "",
  series: "",
  issued_on: "",
};

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

export function FiscalEntryNewPage() {
  const { api, hasPermission } = useOrganization();
  const navigate = useNavigate();
  const command = useCommand();
  const [params] = useSearchParams();

  const requested = params.get("origem");
  const highlighted = isFiscalEntryOption(requested) ? requested : null;

  const [xmlFile, setXmlFile] = useState<File | null>(null);
  const [scanFile, setScanFile] = useState<File | null>(null);
  const [manual, setManual] = useState<ManualForm>(EMPTY_MANUAL);
  const [readError, setReadError] = useState<string | null>(null);
  const [simulationNote, setSimulationNote] = useState<string | null>(null);

  const requestedRef = useRef<HTMLInputElement | null>(null);
  useEffect(() => {
    if (highlighted) requestedRef.current?.focus();
  }, [highlighted]);

  const allowed = canCaptureFiscalDocument(hasPermission);
  const busy = !allowed || command.pending;

  function goToDocument(created: Envelope<FiscalDocument> | null) {
    const id = created?.data?.id;
    if (id) navigate(`/gestao/compras/entradas/${id}`);
  }

  function focusRefFor(slug: string) {
    return highlighted === slug ? requestedRef : undefined;
  }

  /** Enquanto a consulta real está desativada, a demo ingere documentos sintéticos. */
  async function runDistributionSimulation() {
    if (busy) return;
    setReadError(null);
    setSimulationNote(null);
    try {
      const result = await command.run("fiscal-dist-sim", (key) =>
        api.simulateFiscalDistribution({ ingest: true }, key),
      );
      const ingested = result?.data?.documents_ingested as string[] | undefined;
      if (ingested?.length) {
        navigate(`/gestao/compras/entradas/${ingested[0]}`);
        return;
      }
      setSimulationNote(
        typeof result?.data?.x_motivo === "string"
          ? result.data.x_motivo
          : "Simulação concluída sem novos documentos fictícios.",
      );
    } catch {
      /* a mensagem aparece em command.error */
    }
  }

  async function submitXml(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (busy || !xmlFile) return;
    setReadError(null);
    try {
      const content = await readAsText(xmlFile);
      goToDocument(
        await command.run(`fiscal-xml:${xmlFile.name}:${xmlFile.size}`, (key) =>
          api.importFiscalXml({ filename: xmlFile.name, content }, key),
        ),
      );
    } catch (error) {
      if (error instanceof Error && error.message === READ_FAILED) setReadError(error.message);
    }
  }

  async function submitScan(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (busy || !scanFile) return;
    setReadError(null);
    try {
      const content = await readAsDataUrl(scanFile);
      goToDocument(
        await command.run(`fiscal-scan:${scanFile.name}:${scanFile.size}`, (key) =>
          api.attachFiscalScan({ filename: scanFile.name, content }, key),
        ),
      );
    } catch (error) {
      if (error instanceof Error && error.message === READ_FAILED) setReadError(error.message);
    }
  }

  async function submitManual(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (busy || !manual.supplier_name.trim() || !manual.document_number.trim()) return;
    setReadError(null);
    try {
      goToDocument(
        await command.run(`fiscal-manual:${manual.document_number.trim()}`, (key) =>
          api.createManualFiscal(
            {
              supplier_name: manual.supplier_name.trim(),
              supplier_tax_id: manual.supplier_tax_id.replace(/\D/g, "") || null,
              document_number: manual.document_number.trim(),
              series: manual.series.trim() || null,
              issued_on: manual.issued_on || null,
            },
            key,
          ),
        ),
      );
    } catch {
      /* a mensagem aparece em command.error */
    }
  }

  function optionFor(slug: string) {
    const option = FISCAL_ENTRY_OPTIONS.find((row) => row.slug === slug)!;
    return {
      option,
      className: highlighted === slug ? "card entry-option is-highlighted" : "card entry-option",
    };
  }

  const manualOption = optionFor("manual");
  const xml = optionFor("xml");
  const foto = optionFor("foto");
  const fazenda = optionFor("fazenda");

  return (
    <div className="stage">
      <div>
        <div className="page-head">
          <div>
            <h1>Registrar entrada</h1>
          </div>
        </div>
        <p className="lede">
          Escolha por onde é mais rápido hoje. Os quatro caminhos terminam na mesma tela de
          conferência, onde você confere itens, quantidades e só então atualiza o estoque.
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
        {simulationNote ? (
          <p className="meta" role="status">
            {simulationNote}
          </p>
        ) : null}

        <div className="entry-options-grid">
          <section className={manualOption.className} aria-label={manualOption.option.title}>
            <h2>{manualOption.option.title}</h2>
            <p>{manualOption.option.summary}</p>
            <form onSubmit={submitManual}>
              <label>
                Fornecedor
                <input
                  ref={focusRefFor("manual")}
                  value={manual.supplier_name}
                  autoComplete="off"
                  onChange={(event) =>
                    setManual((current) => ({ ...current, supplier_name: event.target.value }))
                  }
                  disabled={busy}
                />
              </label>
              <label>
                CNPJ do fornecedor
                <input
                  value={manual.supplier_tax_id}
                  inputMode="numeric"
                  autoComplete="off"
                  onChange={(event) =>
                    setManual((current) => ({ ...current, supplier_tax_id: event.target.value }))
                  }
                  disabled={busy}
                />
              </label>
              <label>
                Número da nota
                <input
                  value={manual.document_number}
                  inputMode="numeric"
                  autoComplete="off"
                  onChange={(event) =>
                    setManual((current) => ({ ...current, document_number: event.target.value }))
                  }
                  disabled={busy}
                />
              </label>
              <label>
                Série
                <input
                  value={manual.series}
                  autoComplete="off"
                  onChange={(event) =>
                    setManual((current) => ({ ...current, series: event.target.value }))
                  }
                  disabled={busy}
                />
              </label>
              <label>
                Data de emissão
                <input
                  type="date"
                  value={manual.issued_on}
                  onChange={(event) =>
                    setManual((current) => ({ ...current, issued_on: event.target.value }))
                  }
                  disabled={busy}
                />
              </label>
              <button type="submit" className="primary" disabled={busy}>
                {manualOption.option.action}
              </button>
            </form>
          </section>

          <section className={xml.className} aria-label={xml.option.title}>
            <h2>{xml.option.title}</h2>
            <p>{xml.option.summary}</p>
            <form onSubmit={submitXml}>
              <label>
                Arquivo XML da nota
                <input
                  ref={focusRefFor("xml")}
                  type="file"
                  accept=".xml,text/xml,application/xml"
                  onChange={(event) => setXmlFile(event.target.files?.[0] ?? null)}
                  disabled={busy}
                />
              </label>
              <button type="submit" className="primary" disabled={busy}>
                {xml.option.action}
              </button>
            </form>
          </section>

          <section className={foto.className} aria-label={foto.option.title}>
            <h2>{foto.option.title}</h2>
            <p>{foto.option.summary}</p>
            <form onSubmit={submitScan}>
              <label>
                PDF ou foto do DANFE
                <input
                  ref={focusRefFor("foto")}
                  type="file"
                  accept="image/*,application/pdf"
                  capture="environment"
                  onChange={(event) => setScanFile(event.target.files?.[0] ?? null)}
                  disabled={busy}
                />
              </label>
              <p className="meta">
                O arquivo fica anexado à entrada como prova. Os itens continuam sendo conferidos por
                uma pessoa.
              </p>
              <button type="submit" className="primary" disabled={busy}>
                {foto.option.action}
              </button>
            </form>
          </section>

          <section className={fazenda.className} aria-label={fazenda.option.title}>
            <h2>{fazenda.option.title}</h2>
            <p>{fazenda.option.summary}</p>
            <p className="meta" role="status">
              Nenhum certificado A1 está ativo neste estabelecimento. Entradas manuais, XML e PDF/foto
              continuam disponíveis normalmente.
            </p>
            <button
              type="button"
              className="ghost"
              disabled={busy}
              onClick={() => void runDistributionSimulation()}
            >
              Simulação — documentos fictícios DEMONSTRAÇÃO
            </button>
          </section>
        </div>

        <p>
          <Link className="ghost" to="/gestao/compras/entradas">
            Voltar às entradas fiscais
          </Link>
        </p>
      </div>
      <aside className="panel">
        <h2>O que acontece depois</h2>
        <p>
          Qualquer um dos caminhos abre a mesma tela de conferência: documento, fornecedor, itens,
          correspondência com o cadastro, o que chegou, onde foi guardado e quanto custou.
        </p>
        <p>
          Nada é lançado no estoque agora. A entrada só movimenta saldo quando alguém confirma a
          conferência.
        </p>
        <p className="meta">
          A consulta automática à Fazenda está tecnicamente pronta e permanece desativada até
          certificado A1, habilitação do estabelecimento e liberação operacional.
        </p>
      </aside>
    </div>
  );
}
