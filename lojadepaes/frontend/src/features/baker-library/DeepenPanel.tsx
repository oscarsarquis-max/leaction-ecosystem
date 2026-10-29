import { useEffect, useState } from "react";
import { GIGIO_OPEN_EVENT } from "../bread-builder/proposal";
import { setLibraryPageContext } from "../../gigio/session";
import {
  fetchLibraryAccess,
  fetchLibraryPlan,
  moneyLabel,
  type LibraryAccess,
  type LibraryOffer,
  type LibraryPlan,
} from "./libraryApi";

type Props = {
  articleId: string;
  articleVersion: number;
  calculatorMode?: string;
  returnTo: string;
};

function offerPrice(offer: LibraryOffer | undefined, fallback: number, period: string) {
  return moneyLabel(typeof offer?.price === "number" ? offer.price : fallback, offer?.currency, period);
}

export function DeepenPanel({ articleId, articleVersion, calculatorMode = "" }: Props) {
  const [plan, setPlan] = useState<LibraryPlan | null>(null);
  const [access, setAccess] = useState<LibraryAccess | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    Promise.all([fetchLibraryPlan(), fetchLibraryAccess()])
      .then(([nextPlan, nextAccess]) => {
        if (cancelled) return;
        setPlan(nextPlan);
        setAccess(nextAccess);
      })
      .catch(() => {
        if (!cancelled) {
          setMessage("Não foi possível consultar os planos agora.");
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  function openDeepen() {
    setLibraryPageContext({
      article_id: articleId,
      article_version: articleVersion,
      intent: "deepen",
      calculator_mode: calculatorMode,
    });
    window.dispatchEvent(new CustomEvent(GIGIO_OPEN_EVENT));
  }

  const principal = plan?.principal;
  const pack = plan?.pack || plan?.complementary;
  const principalPrice = offerPrice(principal, plan?.authorized_initial_brl ?? 19, "mês");
  const packPrice = offerPrice(pack, plan?.authorized_pack_brl ?? plan?.authorized_complementary_brl ?? 10, "avulso");
  const hubDown = access?.reason === "hub_unavailable" || access?.balance_source === "unavailable" || plan?.source === "unavailable";
  const plansHref = plan?.plans_href || access?.plans_href || "";
  const canDeepen =
    Boolean(access?.identified) &&
    (Boolean(access?.can_use_ai) ||
      Boolean(access?.authorized) ||
      (typeof access?.ai_credits === "number" && access.ai_credits > 0));

  return (
    <aside className="library-deepen" aria-labelledby="library-deepen-title">
      <p className="eyebrow">APROFUNDAR COM O GIGIO</p>
      <h2 id="library-deepen-title">Consultas de IA da Biblioteca</h2>
      <p>
        Os artigos e a calculadora continuam livres. O aprofundamento personalizado usa consultas de
        IA da Biblioteca — uma consulta é uma mensagem enviada neste modo. A franquia da assinatura
        é mensal e não acumula. Pedido, pães, fidelidade e pagamento não gastam este saldo.
      </p>
      <div className="library-plans">
        <article>
          <h3>Assinatura</h3>
          <p className="library-price">{principalPrice}</p>
          <p>{principal?.credits ?? 20} consultas de IA por ciclo · 10% de desconto nos produtos da Loja</p>
        </article>
        <article>
          <h3>Pacote adicional</h3>
          <p className="library-price">{packPrice}</p>
          <p>
            {pack?.credits ?? 10} consultas de IA avulsas, cumulativas e sem vencimento. Não é
            assinatura, não exige plano mensal e não dá desconto de assinante nem crédito de pão.
          </p>
        </article>
      </div>
      <ul>
        {(plan?.benefits || plan?.features || []).map((item) => (
          <li key={item}>{item}</li>
        ))}
      </ul>
      {plan?.message ? <p className="library-note">{plan.message}</p> : null}
      {plansHref ? (
        <a className="primary" href={plansHref}>
          Ver planos
        </a>
      ) : (
        <p className="library-note">A contratação fica na página de planos da Loja.</p>
      )}
      {access?.identified ? (
        <div className="library-balance">
          <p>
            <strong>Assinatura:</strong>{" "}
            {access.subscription_status === "active"
              ? "ativa"
              : access.subscription_status === "pending"
                ? "pendente"
                : access.subscription_status === "cancelled_with_access"
                  ? "renovação cancelada, acesso ainda vigente"
                  : "sem assinatura"}
          </p>
          {access.balance_source === "hub" && typeof access.ai_credits === "number" ? (
            <>
              <p>
                <strong>Consultas do mês:</strong> {access.monthly_credits ?? "—"}
                {access.valid_until
                  ? ` · até ${new Date(access.valid_until).toLocaleDateString("pt-BR")}`
                  : ""}
              </p>
              <p>
                <strong>Pacote avulso:</strong> {access.pack_credits ?? 0} · sem vencimento
              </p>
            </>
          ) : access.authorized ? (
            <p className="library-note">
              A assinatura foi reconhecida, mas o saldo de consultas de IA só aparece quando
              a Loja consegue consultar o saldo.
            </p>
          ) : null}
          {canDeepen && !access.exhausted ? (
            <button type="button" className="primary" onClick={openDeepen}>
              Entrar no aprofundamento com consultas de IA
            </button>
          ) : access.exhausted ? (
            <p>As consultas de IA acabaram. Leitura, contas, compras e atendimento continuam.</p>
          ) : (
            <p className="library-note">
              Identifique-se no cabeçalho da Loja para ver a situação real da conta. O código
              autentica a pessoa; não prova assinatura nem concede crédito.
            </p>
          )}
        </div>
      ) : (
        <p className="library-note">
          A identificação fica no cabeçalho da Loja, com o código enviado ao e-mail cadastrado. Não
          há formulário de acesso neste artigo.
        </p>
      )}
      {hubDown ? (
        <p className="library-note">
          Falha temporária na consulta do saldo não significa saldo esgotado nem assinatura cancelada.
        </p>
      ) : null}
      {message ? (
        <p className="library-note" role="status">
          {message}
        </p>
      ) : null}
    </aside>
  );
}
