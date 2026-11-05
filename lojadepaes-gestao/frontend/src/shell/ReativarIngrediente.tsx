import { useState } from "react";
import { ApiError, reativarIngrediente, textoDoErro, type Juntado } from "../lib/api";
import { Button } from "./Button";
import { Modal } from "./Modal";

function diaMes(iso: string | null): string {
  if (!iso) return "";
  const partes = iso.slice(0, 10).split("-");
  return partes.length === 3 ? `${partes[2]}/${partes[1]}` : "";
}

/** O nome escolhido já foi juntado: reativar não devolve os itens, só libera o ingrediente. */
export function ReativarIngredienteDialog({
  juntado,
  onFechar,
  onReativado,
}: {
  juntado: Juntado;
  onFechar: () => void;
  onReativado: () => void;
}) {
  const [motivo, setMotivo] = useState("");
  const [erro, setErro] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);
  const quando = diaMes(juntado.juntado_em);
  const pronto = motivo.trim().length >= 3;

  return (
    <Modal titulo="Reativar ingrediente" onFechar={onFechar}>
      <form
        className="painel-form"
        aria-label={`Reativar ${juntado.nome}`}
        onSubmit={(event) => {
          event.preventDefault();
          if (!pronto || enviando) return;
          setEnviando(true);
          setErro(null);
          void reativarIngrediente(juntado.id, motivo.trim())
            .then(() => onReativado())
            .catch((falha: unknown) => {
              setErro(falha instanceof ApiError ? textoDoErro(falha) : "Não foi possível reativar agora.");
              setEnviando(false);
            });
        }}
      >
        <p className="mover-frase">
          <strong>{juntado.nome}</strong> foi juntado
          {juntado.destino_nome ? (
            <>
              {" "}
              a <em>{juntado.destino_nome}</em>
            </>
          ) : null}
          {quando ? ` em ${quando}` : ""}.
        </p>
        <p className="sub">Reativar não move nada de volta. A troca dos itens continua com você.</p>
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
          <Button type="submit" variant="primary" disabled={enviando || !pronto}>
            Reativar como ingrediente separado
          </Button>
          <Button onClick={onFechar}>Cancelar</Button>
        </div>
      </form>
    </Modal>
  );
}
