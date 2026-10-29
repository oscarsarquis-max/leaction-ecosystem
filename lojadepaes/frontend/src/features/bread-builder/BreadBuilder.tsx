import { useEffect, useRef, useState } from "react";
import { OptionCard } from "../../components/OptionCard";
import { BakeCalendar } from "../../shop/BakeCalendar";
import { isDaySelectable } from "../../shop/calendarDays";
import type { CalendarDay, CalendarLine } from "../../shop/calendarApi";
import { useCart } from "../../shop/CartContext";
import { CartAddedNotice } from "../../shop/CartAddedNotice";
import { fetchBuilderCatalog, fetchBuilderProposal, type BuilderCatalog, type BuilderProposal, type BuilderTip } from "./builderApi";
import { NEXT_LABELS, PHOTOS, STEP_DESCRIPTIONS, STEP_HEADINGS, STEP_LABELS } from "./catalog";
import { GigioLoafTip } from "./GigioLoafTip";
import {
  BUILDER_PROPOSAL_EVENT,
  hasBuilderWork,
  proposalDiffers,
  proposalSearchToken,
  proposalToPartial,
} from "./proposal";
import {
  BUILDER_RESUME_KEY,
  chosenIngredientIds,
  chosenIngredientNames,
  formatCommercialLine,
  formatLoafPrice,
} from "./state";
import { useBreadBuilder } from "./useBreadBuilder";

const PREFERRED_DATE_KEY = "lojadepaes_preferred_date";

export function BreadBuilder() {
  const builder = useBreadBuilder();
  const cart = useCart();
  const {
    state,
    selectMass,
    selectFlour,
    toggleIngredient,
    selectShape,
    selectDate,
    setFreeText,
    setQuantity,
    setPrice,
    next,
    back,
    restart,
    applyResume,
    applyPatch,
    canFinish,
    canAdvance,
    tip,
    summary,
    receipt,
  } = builder;
  const contentRef = useRef<HTMLDivElement>(null);
  const [catalog, setCatalog] = useState<BuilderCatalog | null>(null);
  const [catalogError, setCatalogError] = useState<string | null>(null);
  const [dateNotice, setDateNotice] = useState<string | null>(null);
  const [gigioEnabled, setGigioEnabled] = useState(false);
  const [addedToCart, setAddedToCart] = useState(false);
  const [pendingProposal, setPendingProposal] = useState<BuilderProposal | null>(null);
  const [proposalError, setProposalError] = useState<string | null>(null);
  const loadingToken = useRef<string>("");
  const stateRef = useRef(state);
  stateRef.current = state;

  useEffect(() => {
    let cancelled = false;
    fetchBuilderCatalog()
      .then((payload) => {
        if (cancelled) return;
        setCatalog(payload);
        setPrice(payload.price_cents, payload.weight_grams);
        setCatalogError(null);
      })
      .catch(() => {
        if (!cancelled) setCatalogError("Não foi possível carregar as opções de A Loja. Tente de novo.");
      });
    return () => {
      cancelled = true;
    };
  }, [setPrice]);

  useEffect(() => {
    try {
      const raw = sessionStorage.getItem(BUILDER_RESUME_KEY);
      if (!raw) return;
      const draft = JSON.parse(raw) as {
        massId?: string;
        massName?: string;
        flourId?: string;
        flourName?: string;
        extraIds?: string[];
        extraNames?: string[];
        shapeId?: string;
        shapeName?: string;
        freeText?: string;
        quantity?: number;
        notice?: string;
      };
      sessionStorage.removeItem(BUILDER_RESUME_KEY);
      applyResume(
        {
          massId: draft.massId ?? "",
          massName: draft.massName ?? "",
          flourId: draft.flourId ?? "",
          flourName: draft.flourName ?? "",
          extraIds: draft.extraIds ?? [],
          extraNames: draft.extraNames ?? [],
          shapeId: draft.shapeId ?? "",
          shapeName: draft.shapeName ?? "",
          freeText: draft.freeText ?? "",
          quantity: draft.quantity ?? 1,
        },
        draft.notice,
      );
    } catch {
      sessionStorage.removeItem(BUILDER_RESUME_KEY);
    }
  }, [applyResume]);

  useEffect(() => {
    let cancelled = false;
    fetch("/api/v1/gigio/status")
      .then((response) => (response.ok ? response.json() : { enabled: false }))
      .then((payload) => {
        if (!cancelled) setGigioEnabled(Boolean(payload.enabled));
      })
      .catch(() => {
        if (!cancelled) setGigioEnabled(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  function applyProposal(proposal: BuilderProposal) {
    applyResume({
      ...proposalToPartial(proposal),
      gigioNotice: proposal.notice || "Sugestão do Gigio. Você pode alterar.",
    });
    setPendingProposal(null);
    setProposalError(null);
  }

  function receiveProposal(token: string) {
    if (!token || loadingToken.current === token) {
      return;
    }
    loadingToken.current = token;
    fetchBuilderProposal(token)
      .then((proposal) => {
        const current = stateRef.current;
        if (hasBuilderWork(current) && proposalDiffers(current, proposal)) {
          setPendingProposal(proposal);
          return;
        }
        applyProposal(proposal);
      })
      .catch(() => {
        setProposalError("Esta sugestão do Gigio não pôde ser aplicada. As opções atuais foram mantidas.");
      })
      .finally(() => {
        if (loadingToken.current === token) {
          loadingToken.current = "";
        }
      });
  }

  useEffect(() => {
    const token = proposalSearchToken();
    if (token) {
      receiveProposal(token);
    }
    const onProposal = (event: Event) => {
      const detail = (event as CustomEvent<{ token?: string }>).detail;
      if (detail?.token) {
        receiveProposal(detail.token);
      }
    };
    window.addEventListener(BUILDER_PROPOSAL_EVENT, onProposal);
    return () => window.removeEventListener(BUILDER_PROPOSAL_EVENT, onProposal);
    // Intentionally bind once after mount; receiveProposal reads current state.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    contentRef.current?.focus();
  }, [state.step, state.finished]);

  function applyTipSuggestion(tipPayload: BuilderTip) {
    const patch = tipPayload.suggestion?.patch;
    if (!patch) return;
    applyPatch(
      {
        flourId: patch.flour_id || state.flourId,
        flourName: patch.flour_name || state.flourName,
        massId: patch.dough_id || state.massId,
        massName: patch.dough_name || state.massName,
        extraIds: patch.ingredient_ids || state.extraIds,
        extraNames: patch.ingredient_names || state.extraNames,
        shapeId: patch.shape_id || state.shapeId,
        shapeName: patch.shape_name || state.shapeName,
      },
      "Sugestão do Gigio aplicada. Quantidade e observações foram mantidas.",
    );
  }

  const previewTitle = state.massName || (
    <>
      Simples na essência.
      <br />
      Extraordinário no sabor.
    </>
  );

  const priceLabel = formatLoafPrice(state.priceCents, state.weightGrams);
  const calendarLines: CalendarLine[] = state.quantity
    ? [{ kind: "custom", quantity: state.quantity, dough_type_id: state.massId || undefined }]
    : [];

  function rememberCreatorDay(day: CalendarDay | null) {
    if (!state.date || !day) {
      return;
    }
    if (!day.eligible || !isDaySelectable(day)) {
      selectDate("");
      setDateNotice(
        day.accessible_label || "Esta data não comporta esta composição. Escolha outra data.",
      );
      return;
    }
    setDateNotice(null);
  }
  const nextDisabled =
    (state.step === 0 && !canAdvance) ||
    (state.step === 2 && !state.shapeId) ||
    (state.step === 3 && !canFinish);

  function sendOrder() {
    const dough = catalog?.doughs.find((item) => item.id === state.massId);
    const shape = catalog?.shapes.find((item) => item.id === state.shapeId);
    if (!dough || !shape || state.priceCents <= 0) return;
    sessionStorage.setItem(PREFERRED_DATE_KEY, state.date);
    cart.addCustom(
      {
        doughTypeId: dough.id,
        breadShapeId: shape.id,
        ingredientIds: chosenIngredientIds(state),
        doughName: dough.name,
        shapeName: shape.name,
        ingredientNames: chosenIngredientNames(state),
        flourId: state.flourId || undefined,
        flourName: state.flourName || undefined,
        weightGrams: state.weightGrams,
        unitCents: state.priceCents,
      },
      state.quantity,
      state.freeText.trim() ? { text: state.freeText.trim(), reason: "preference" } : null,
    );
    setAddedToCart(true);
  }

  return (
    <section id="criacao" className="studio" aria-labelledby="criador-titulo">
      <div className="workspace">
        <header className="studio-intro">
          <h2 id="criador-titulo" className="studio-title">
            Criador de Pães
          </h2>
          <p className="studio-lead">
            Elabore sua receita e deixe que a gente use a técnica para entregar o melhor pão do mundo.
          </p>
        </header>
        <div className="steps" aria-label="Etapas da criação">
          {STEP_LABELS.map((label, index) => {
            const current = index === state.step && !state.finished;
            const done = index < state.step || state.finished;
            return (
              <div
                key={label}
                className={`step ${current ? "current" : ""} ${done ? "done" : ""}`}
                aria-current={current ? "step" : undefined}
              >
                <i>{done ? "✓" : index + 1}</i>
                <span>{label}</span>
              </div>
            );
          })}
        </div>
        <div id="step-content" ref={contentRef} tabIndex={-1}>
          {catalogError ? <p className="tip">{catalogError}</p> : null}
          {state.gigioNotice ? (
            <p className="tip" role="status">
              {state.gigioNotice}
            </p>
          ) : null}
          {proposalError ? (
            <p className="tip" role="status">
              {proposalError}
            </p>
          ) : null}
          {pendingProposal ? (
            <div className="gigio-loaf-confirm" role="dialog" aria-labelledby="gigio-overwrite-title">
              <p id="gigio-overwrite-title">
                Você já está montando outro pão. Manter o atual ou aplicar a sugestão do Gigio?
              </p>
              <button type="button" className="text-button" onClick={() => setPendingProposal(null)}>
                Manter o atual
              </button>
              <button type="button" className="primary" onClick={() => applyProposal(pendingProposal)}>
                Aplicar a sugestão
              </button>
            </div>
          ) : null}
          {state.finished ? (
            <div className="success">
              <p className="step-eyebrow">REVISÃO</p>
              <h2>Confira o pão antes de enviar.</h2>
              <div className="receipt">
                <strong>{receipt[0]}</strong>
                <br />
                {receipt[1]}
                <br />
                {receipt[2]}
                <br />
                {receipt[3]}
              </div>
              <p>{summary}</p>
              <p>
                {state.quantity} × {priceLabel}. Total de{" "}
                {((state.priceCents * state.quantity) / 100).toLocaleString("pt-BR", {
                  style: "currency",
                  currency: "BRL",
                })}
                . Retirada em A Loja. A data é uma preferência.
              </p>
              <p className="fornada-note">
                Isso ainda não envia o pedido. Adicionar ao carrinho guarda esta receita junto com os outros pães.
                A compra só é enviada em Finalizar compra.
              </p>
              {addedToCart ? (
                <CartAddedNotice />
              ) : (
                <button id="send-order" className="primary" type="button" onClick={sendOrder} disabled={state.priceCents <= 0}>
                  Adicionar ao carrinho
                </button>
              )}
              <button id="restart" className="text-button" type="button" onClick={restart}>
                Ajustar escolhas →
              </button>
            </div>
          ) : (
            <>
              <p className="step-eyebrow">PASSO 0{state.step + 1}</p>
              <h3 className="step-heading">{STEP_HEADINGS[state.step]}</h3>
              <p className="desc">{STEP_DESCRIPTIONS[state.step]}</p>
              {state.step === 0 ? (
                <div className="options">
                  <fieldset className="choice-group">
                    <legend className="step-group-title">Farinha</legend>
                    <div className="choice-grid">
                      {(catalog?.flours ?? []).map((flour) => (
                        <OptionCard
                          key={flour.id}
                          title={flour.name}
                          description={flour.description}
                          selected={state.flourId === flour.id}
                          onSelect={() => selectFlour(flour.id, flour.name)}
                        />
                      ))}
                    </div>
                    {catalog && catalog.flours.length === 0 ? (
                      <p>Nenhuma farinha disponível no cadastro de A Loja.</p>
                    ) : null}
                  </fieldset>
                  <fieldset className="choice-group">
                    <legend className="step-group-title">Fermentação e preparo</legend>
                    <div className="choice-grid">
                      {(catalog?.doughs ?? []).map((mass) => (
                        <OptionCard
                          key={mass.id}
                          title={mass.name}
                          description={mass.description}
                          selected={state.massId === mass.id}
                          onSelect={() =>
                            selectMass(
                              mass.id,
                              mass.name,
                              (catalog?.ingredients ?? []).filter((item) => state.extraIds.includes(item.id)),
                            )
                          }
                        />
                      ))}
                    </div>
                    {catalog && catalog.doughs.length === 0 ? (
                      <p>Nenhum preparo disponível no cadastro de A Loja.</p>
                    ) : null}
                  </fieldset>
                  {state.inclusionNotice ? <p className="tip">{state.inclusionNotice}</p> : null}
                </div>
              ) : null}
              {state.step === 1 ? (
                <>
                  <div className="ingredient-grid">
                    {(catalog?.ingredients ?? []).map((ingredient) => (
                      <OptionCard
                        key={ingredient.id}
                        title={ingredient.name}
                        description={ingredient.description}
                        selected={state.extraIds.includes(ingredient.id)}
                        multiple
                        onSelect={() => toggleIngredient(ingredient.id, ingredient.name)}
                      />
                    ))}
                  </div>
                  {catalog && catalog.ingredients.length === 0 ? (
                    <p>
                      Nenhum complemento cadastrado no momento. Você ainda pode pedir um ingrediente livre abaixo. A
                      Loja avalia o pedido antes de aceitar.
                    </p>
                  ) : null}
                  <div className="free-ingredient">
                    <label htmlFor="free-ingredient-text">Quer incluir outro ingrediente?</label>
                    <textarea
                      id="free-ingredient-text"
                      value={state.freeText}
                      maxLength={500}
                      placeholder="Ex.: pepperoni…"
                      onChange={(event) => setFreeText(event.target.value)}
                    />
                    <p className="free-ingredient-help">
                      Conte o que gostaria de acrescentar. A Loja avaliará seu pedido antes de aceitar.
                    </p>
                    <p className="free-ingredient-count">{state.freeText.length}/500</p>
                    <p className="free-ingredient-commercial">
                      {formatCommercialLine(state.priceCents, state.weightGrams)}
                    </p>
                  </div>
                  <div className="tip" aria-live="polite">
                    <strong>Dica do padeiro</strong>
                    <br />
                    {tip}
                  </div>
                  <p className="demo">
                    Contém glúten. Informações sobre alergênicos precisam ser confirmadas por A Loja. O aceite não
                    certifica ausência de alergênicos.
                  </p>
                </>
              ) : null}
              {state.step === 2 ? (
                <div className="options">
                  {(catalog?.shapes ?? []).map((form) => (
                    <OptionCard
                      key={form.id}
                      title={form.name}
                      description={form.description}
                      selected={state.shapeId === form.id}
                      onSelect={() => selectShape(form.id, form.name)}
                    />
                  ))}
                  <GigioLoafTip state={state} enabled={gigioEnabled} onApply={applyTipSuggestion} />
                </div>
              ) : null}
              {state.step === 3 ? (
                <div className="builder-meet">
                  <p>{priceLabel} por pão. A quantidade é o número de pães.</p>
                  <label className="builder-quantity">
                    Quantidade
                    <input
                      type="number"
                      min={1}
                      max={20}
                      value={state.quantity}
                      onChange={(event) => setQuantity(Number(event.target.value))}
                    />
                  </label>
                  <BakeCalendar
                    lines={calendarLines}
                    selectedDate={state.date || null}
                    onSelectDate={(date) => {
                      setDateNotice(null);
                      selectDate(date);
                    }}
                    onSelectedDayChange={rememberCreatorDay}
                    layout="checkout"
                  />
                  {dateNotice ? (
                    <p className="tip" role="status">
                      {dateNotice} A receita continua guardada.
                    </p>
                  ) : (
                    <p className="fornada-note">
                      A data escolhida é uma preferência e só fica reservada depois que A Loja aceitar.
                      Selecionar o dia não reserva nem confirma a entrega.
                    </p>
                  )}
                </div>
              ) : null}
            </>
          )}
        </div>
        <div className="wizard-footer">
          <button
            id="back"
            className="text-button"
            type="button"
            onClick={back}
            hidden={state.finished}
            style={{ visibility: state.step === 0 ? "hidden" : "visible" }}
          >
            ← Voltar
          </button>
          <span id="step-label">{state.step + 1} de 4 passos</span>
          <button id="next" className="primary" type="button" onClick={next} hidden={state.finished} disabled={nextDisabled}>
            {NEXT_LABELS[state.step]} <span>→</span>
          </button>
        </div>
      </div>
      <aside className="bread-preview">
        <div className="preview-photo">
          <img src={PHOTOS.panelHero.src} alt={PHOTOS.panelHero.alt} />
        </div>
        <div
          className="bread-preview-board preview-board"
          style={{ ["--preview-texture" as string]: `url("${PHOTOS.textureFlour.src}")` }}
        >
          <div className="preview-copy">
            <div className="photo-label">DO PRIMEIRO GRÃO À SUA MESA</div>
            <div className="preview-caption">
              <span id="preview-kicker">
                {state.step === 0 && !state.finished ? "O começo de uma boa história" : "A sua próxima fornada"}
              </span>
              <h3 id="preview-title">{previewTitle}</h3>
              <div id="summary" aria-live="polite">
                {summary}
              </div>
            </div>
          </div>
        </div>
      </aside>
    </section>
  );
}
