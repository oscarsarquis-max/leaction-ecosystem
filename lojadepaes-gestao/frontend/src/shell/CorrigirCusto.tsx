import { useEffect, useState, type FormEvent } from "react";
import { corrigirCusto, custoDoLote, textoDoErro, type CustoDoLote, type ModoCusto } from "../lib/api";
import { numero } from "../lib/entradaForm";
import { custoTexto, dinheiro, quantidadeBase } from "../lib/format";
import { Button } from "./Button";
import { Modal } from "./Modal";

/** "R$ por kg", "R$ por L" ou "R$ por embalagem", conforme o item. */
function precoPor(lote: CustoDoLote): string {
  return lote.unidade_controle === "massa" ? "R$ por kg" : lote.unidade_controle === "volume" ? "R$ por L" : "R$ por embalagem";
}

/** O que o servidor vai gravar (R$ por g, ml ou un) para o que foi digitado: a mesma conta, para mostrar antes. */
export function custoDepois(lote: CustoDoLote, modo: ModoCusto, valor: number): number | null {
  if (modo === "valor_pago") return lote.quantidade_comprada_base > 0 ? valor / lote.quantidade_comprada_base : null;
  if (lote.unidade_controle === "embalagem") return lote.conteudo_embalagem ? valor / lote.conteudo_embalagem : null;
  return valor / 1000;
}

function mostrar(lote: CustoDoLote, custoBase: number | null): string {
  if (custoBase === null) return "sem custo informado";
  const porEmbalagem = lote.unidade_controle === "embalagem" && lote.conteudo_embalagem ? custoBase * lote.conteudo_embalagem : null;
  return custoTexto(custoBase, lote.unidade_base, porEmbalagem);
}

/**
 * "Corrigir custo" de um lote: pede o valor pago (ou o preço por unidade) e o motivo, e mostra antes e depois.
 * Custo não é movimento de saldo: nada aqui muda a quantidade, só o custo e o histórico.
 */
export function CorrigirCusto({
  loteId,
  onCancelar,
  onFeito,
}: {
  loteId: string;
  onCancelar: () => void;
  onFeito: () => void;
}) {
  const [lote, setLote] = useState<CustoDoLote | null>(null);
  const [falhou, setFalhou] = useState(false);
  const [modo, setModo] = useState<ModoCusto>("valor_pago");
  const [valor, setValor] = useState("");
  const [motivo, setMotivo] = useState("");
  const [enviando, setEnviando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);

  useEffect(() => {
    let ativo = true;
    custoDoLote(loteId)
      .then((dados) => ativo && setLote(dados))
      .catch(() => ativo && setFalhou(true));
    return () => {
      ativo = false;
    };
  }, [loteId]);

  if (falhou) {
    return (
      <Modal titulo="Corrigir custo" onFechar={onCancelar}>
        <p role="alert" className="form-erro">
          Não foi possível abrir o custo deste lote agora.
        </p>
        <Button onClick={onCancelar}>Fechar</Button>
      </Modal>
    );
  }
  if (!lote) {
    return (
      <Modal titulo="Corrigir custo" onFechar={onCancelar}>
        <p>Carregando.</p>
      </Modal>
    );
  }

  const digitado = numero(valor);
  const depois = digitado === null || digitado < 0 ? null : custoDepois(lote, modo, digitado);
  const igual = depois !== null && lote.custo_unidade_base !== null && Math.abs(depois - lote.custo_unidade_base) < 1e-9;
  const podeEnviar = !enviando && depois !== null && !igual && motivo.trim().length >= 3;

  async function enviar(event: FormEvent) {
    event.preventDefault();
    if (!podeEnviar || digitado === null) return;
    setEnviando(true);
    setErro(null);
    try {
      await corrigirCusto(loteId, {
        ...(modo === "valor_pago" ? { valor_pago: digitado } : { preco_unidade: digitado }),
        motivo: motivo.trim(),
      });
      onFeito();
    } catch (falha) {
      setErro(textoDoErro(falha));
      setEnviando(false);
    }
  }

  return (
    <Modal titulo="Corrigir custo" onFechar={onCancelar}>
    <form className="painel-form corrigir-custo" aria-label={`Corrigir custo do lote ${lote.codigo}`} onSubmit={(e) => void enviar(e)}>
      <p className="sub">
        Lote {lote.codigo} · {lote.item}. Neste lote entraram {quantidadeBase(lote.quantidade_comprada_base, lote.unidade_base)}
        {lote.valor_pago_atual !== null ? `, pagos ${dinheiro(lote.valor_pago_atual)}` : ", sem custo informado"}. O saldo não muda: só o
        custo e o histórico.
      </p>
      <label className="gestao-field">
        <span>Como informar</span>
        <select
          value={modo}
          onChange={(e) => {
            setModo(e.target.value as ModoCusto);
            setValor("");
          }}
        >
          <option value="valor_pago">Valor pago (total do lote)</option>
          <option value="preco_unidade">Preço por unidade ({precoPor(lote)})</option>
        </select>
      </label>
      <label className="gestao-field">
        <span>{modo === "valor_pago" ? "Valor pago (R$)" : `Preço (${precoPor(lote)})`}</span>
        <input type="text" inputMode="decimal" value={valor} autoComplete="off" onChange={(e) => setValor(e.target.value)} />
      </label>
      <dl className="antes-depois" aria-live="polite">
        <div>
          <dt>Antes</dt>
          <dd>{mostrar(lote, lote.custo_unidade_base)}</dd>
        </div>
        <div>
          <dt>Depois</dt>
          <dd>{depois === null ? "—" : mostrar(lote, depois)}</dd>
        </div>
      </dl>
      {igual ? <p className="sub">Igual ao custo atual: nada a corrigir.</p> : null}
      <label className="gestao-field">
        <span>Motivo (obrigatório)</span>
        <input type="text" value={motivo} maxLength={300} onChange={(e) => setMotivo(e.target.value)} />
      </label>
      {erro ? (
        <p role="alert" className="form-erro">
          {erro}
        </p>
      ) : null}
      <div className="painel-acoes">
        <Button type="submit" variant="primary" disabled={!podeEnviar}>
          Gravar correção
        </Button>
        <Button onClick={onCancelar}>Cancelar</Button>
      </div>
    </form>
    </Modal>
  );
}
