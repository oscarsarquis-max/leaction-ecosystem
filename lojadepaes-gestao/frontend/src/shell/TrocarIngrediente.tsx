import { useState } from "react";
import { quantidadeBase } from "../lib/format";
import { Button } from "./Button";
import { CampoIngrediente, type IngredienteEscolhido } from "./CampoIngrediente";
import { Modal } from "./Modal";

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
          if (pronto && novo) onMover(novo.id, motivo.trim(), novo.nome);
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
          placeholder="Buscar o ingrediente certo"
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
        <div className="painel-acoes">
          <Button type="submit" variant="primary" disabled={enviando || !pronto}>
            Mover
          </Button>
          <Button onClick={onCancelar}>Cancelar</Button>
        </div>
      </form>
    </Modal>
  );
}
