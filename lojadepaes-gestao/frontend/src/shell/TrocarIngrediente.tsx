import { useState } from "react";
import { ApiError, textoDoErro, type Juntado } from "../lib/api";
import { quantidadeBase } from "../lib/format";
import { Button } from "./Button";
import { CampoIngrediente, type IngredienteEscolhido } from "./CampoIngrediente";
import { Modal } from "./Modal";
import { ReativarIngredienteDialog } from "./ReativarIngrediente";

const BASES: Record<string, string> = { g: "Massa (g)", ml: "Volume (ml)", un: "Unidade (un)" };

/** "Trocar ingrediente" é ação do item: diz o que sai, para onde, e grava com motivo. */
export function TrocarIngredienteDialog({
  item,
  marca,
  origem,
  origemId,
  unidadeBase,
  lotes,
  saldo,
  enviando,
  onCancelar,
  onMover,
}: {
  item: string;
  marca: string;
  origem: string;
  origemId: string;
  unidadeBase: string;
  lotes: number;
  saldo: number;
  enviando: boolean;
  onCancelar: () => void;
  onMover: (ingredienteId: string, motivo: string, nome: string) => void;
}) {
  const [novo, setNovo] = useState<IngredienteEscolhido | null>(null);
  const [motivo, setMotivo] = useState("");
  const [erro, setErro] = useState<string | null>(null);
  const [ficha, setFicha] = useState<Juntado | null>(null);
  const [reativar, setReativar] = useState(false);
  const outraUnidade = novo !== null && novo.unidade_base !== unidadeBase;
  const mesmo = novo !== null && novo.id === origemId;
  const pronto = novo !== null && !outraUnidade && !mesmo && motivo.trim().length >= 3;
  const lotesTexto = `${lotes} ${lotes === 1 ? "lote" : "lotes"}`;

  return (
    <Modal titulo="Trocar ingrediente" onFechar={onCancelar}>
      <form
        className="painel-form"
        aria-label={`Trocar o ingrediente de ${item}`}
        onSubmit={(event) => {
          event.preventDefault();
          if (!pronto || !novo) return;
          setErro(null);
          void Promise.resolve(onMover(novo.id, motivo.trim(), novo.nome)).catch((falha: unknown) => {
            setErro(textoDoErro(falha));
            const ficha =
              falha instanceof ApiError
                ? (falha.detalhe as { reativar?: Juntado } | null)?.reativar
                : undefined;
            if (ficha) setFicha(ficha);
          });
        }}
      >
        <p className="mover-frase">
          Mover <strong>{item}</strong> ({lotesTexto}, {quantidadeBase(saldo, unidadeBase)}) de <em>{origem}</em> para:
        </p>
        <CampoIngrediente
          rotulo="Novo ingrediente do item"
          valor={novo ? { nome: novo.nome, categoria: novo.categoria } : null}
          item={item}
          marca={marca}
          placeholder="Buscar ingrediente de destino"
          excluirId={origemId}
          onEscolher={(ing) => setNovo(ing)}
          onTrocar={() => setNovo(null)}
        />
        {outraUnidade ? (
          <p role="alert" className="form-erro">
            “{novo?.nome}” é medido em outra unidade ({BASES[novo?.unidade_base ?? ""] ?? novo?.unidade_base}). Escolha um ingrediente em{" "}
            {BASES[unidadeBase] ?? unidadeBase}.
          </p>
        ) : null}
        {mesmo ? <p className="sub">Este item já está ligado a “{origem}”.</p> : null}
        <label className="gestao-field">
          <span>Motivo (obrigatório)</span>
          <input type="text" value={motivo} maxLength={300} onChange={(e) => setMotivo(e.target.value)} />
        </label>
        {erro ? (
          <div role="alert" className="form-erro">
            <p>{erro}</p>
            {ficha ? (
              <Button onClick={() => setReativar(true)}>Reativar como ingrediente separado</Button>
            ) : null}
          </div>
        ) : null}
        <div className="painel-acoes">
          <Button type="submit" variant="primary" disabled={enviando || !pronto}>
            Mover
          </Button>
          <Button onClick={onCancelar}>Cancelar</Button>
        </div>
      </form>
      {reativar && ficha ? (
        <ReativarIngredienteDialog
          juntado={ficha}
          onFechar={() => setReativar(false)}
          onReativado={() => {
            setReativar(false);
            setFicha(null);
            setErro(null);
            setNovo(null);
          }}
        />
      ) : null}
    </Modal>
  );
}
