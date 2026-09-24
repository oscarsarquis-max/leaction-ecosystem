import { useState } from "react";
import { ADAPTATION_TEXT_MAX, normalizedAdaptation, type AdaptationDraft } from "./selection";
import { useCart } from "./CartContext";
import type { ResolvedLine } from "./types";

export const ADAPTATION_HELP =
  "Descreva sua necessidade. Vamos avaliar a possibilidade antes de confirmar seu pedido. A alteração ainda não está garantida.";

export const DIETARY_DISCLAIMER =
  "Esta solicitação não garante ausência de alergênicos nem evita contato cruzado na padaria. Não tratamos o pedido como livre de um alergênico específico.";

export function reasonLabel(reason: AdaptationDraft["reason"] | string | null | undefined): string | null {
  if (reason === "preference") {
    return "Preferência";
  }
  if (reason === "dietary_restriction") {
    return "Intolerância ou restrição alimentar";
  }
  return null;
}

export function adaptationStatusLabel(status: string, clientDecision?: string | null): string {
  if (status === "accepted") {
    return "A padaria avaliou que consegue atender esta adaptação conforme solicitada. Isso registra a avaliação da padaria, não uma certificação de ausência de alergênicos.";
  }
  if (status === "alternative_accepted") {
    return "Você concordou com a alternativa proposta pela padaria.";
  }
  if (status === "declined") {
    return "A padaria informou que não consegue atender esta adaptação. O item não será preparado como um pão sem alteração. Cancelar o pedido não devolve o pagamento automaticamente.";
  }
  if (status === "alternative_proposed" && clientDecision === "declined") {
    return "Você recusou a alternativa. A padaria precisa propor outra opção ou tratar o pedido pelo fluxo de cancelamento. Cancelar não devolve o pagamento automaticamente.";
  }
  if (status === "alternative_proposed") {
    return "A padaria propôs uma alternativa. Ela só vale se você concordar explicitamente abaixo. Silêncio não confirma.";
  }
  return "Adaptação solicitada — aguardando avaliação da padaria. A alteração ainda não está garantida.";
}

type FieldsProps = {
  value: AdaptationDraft;
  onChange: (next: AdaptationDraft) => void;
  idPrefix: string;
};

export function AdaptationFields({ value, onChange, idPrefix }: FieldsProps) {
  const helpId = `${idPrefix}-help`;
  const dietaryId = `${idPrefix}-dietary`;
  return (
    <div className="adaptation-fields">
      <p className="adaptation-question">O que você gostaria de mudar?</p>
      <label htmlFor={`${idPrefix}-text`}>
        Ingrediente a retirar, substituir ou outra preferência
        <textarea
          id={`${idPrefix}-text`}
          value={value.text}
          maxLength={ADAPTATION_TEXT_MAX}
          rows={3}
          aria-describedby={`${helpId}${value.reason === "dietary_restriction" ? ` ${dietaryId}` : ""}`}
          onChange={(event) => onChange({ ...value, text: event.target.value.slice(0, ADAPTATION_TEXT_MAX) })}
        />
      </label>
      <p className="adaptation-count">
        {value.text.length}/{ADAPTATION_TEXT_MAX}
      </p>
      <fieldset className="adaptation-reason">
        <legend>Motivo (opcional)</legend>
        <label>
          <input
            type="radio"
            name={`${idPrefix}-reason`}
            checked={value.reason === "preference"}
            onChange={() => onChange({ ...value, reason: "preference" })}
          />
          Preferência
        </label>
        <label>
          <input
            type="radio"
            name={`${idPrefix}-reason`}
            checked={value.reason === "dietary_restriction"}
            onChange={() => onChange({ ...value, reason: "dietary_restriction" })}
          />
          Intolerância ou restrição alimentar
        </label>
        {value.reason ? (
          <button
            type="button"
            className="text-button"
            onClick={() => onChange({ ...value, reason: "" })}
          >
            Sem motivo informado
          </button>
        ) : null}
      </fieldset>
      <p id={helpId} className="adaptation-help">
        {ADAPTATION_HELP}
      </p>
      {value.reason === "dietary_restriction" ? (
        <p id={dietaryId} className="adaptation-disclaimer" role="note">
          {DIETARY_DISCLAIMER}
        </p>
      ) : null}
    </div>
  );
}

type DisclosureProps = {
  value: AdaptationDraft;
  onChange: (next: AdaptationDraft) => void;
};

export function AdaptationDisclosure({ value, onChange }: DisclosureProps) {
  const filled = Boolean(value.text.trim());
  return (
    <details className="adaptation-disclosure">
      <summary>{filled ? "Pedir uma adaptação (solicitação preenchida)" : "Pedir uma adaptação"}</summary>
      <AdaptationFields value={value} onChange={onChange} idPrefix="product-adaptation" />
    </details>
  );
}

export function AdaptationLineNote({
  adaptation,
  quantity,
}: {
  adaptation?: AdaptationDraft | null;
  quantity: number;
}) {
  if (!adaptation?.text.trim()) {
    return null;
  }
  const reason = reasonLabel(adaptation.reason);
  return (
    <p className="adaptation-line-note">
      <strong>Adaptação solicitada</strong>
      {reason ? ` · ${reason}` : ""}: {adaptation.text.trim()}
      {quantity > 1
        ? ` Vale para as ${quantity} unidades desta linha. Para um pedido diferente, adicione outra linha.`
        : " Vale para esta linha. Para um pedido diferente, adicione outra linha."}
    </p>
  );
}

export function AdaptationLineEditor({ line }: { line: ResolvedLine }) {
  const cart = useCart();
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState<AdaptationDraft>(line.adaptation ?? { text: "", reason: "" });

  function save() {
    cart.changeAdaptation(line.key, normalizedAdaptation(draft));
    setEditing(false);
  }

  return (
    <>
      <AdaptationLineNote adaptation={line.adaptation} quantity={line.quantity} />
      {editing ? (
        <div className="adaptation-line-edit">
          <AdaptationFields value={draft} onChange={setDraft} idPrefix={`line-${line.key}`} />
          <div className="adaptation-line-actions">
            <button type="button" className="text-button" onClick={save}>
              Guardar adaptação
            </button>
            <button type="button" className="text-button" onClick={() => setEditing(false)}>
              Cancelar
            </button>
          </div>
        </div>
      ) : (
        <div className="adaptation-line-actions">
          <button
            type="button"
            className="text-button"
            onClick={() => {
              setDraft(line.adaptation ?? { text: "", reason: "" });
              setEditing(true);
            }}
          >
            {line.adaptation ? "Editar adaptação" : "Pedir uma adaptação"}
          </button>
          {line.adaptation ? (
            <button type="button" className="text-button" onClick={() => cart.changeAdaptation(line.key, null)}>
              Remover adaptação
            </button>
          ) : null}
        </div>
      )}
    </>
  );
}
