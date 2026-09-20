import { useEffect, useRef } from "react";
import { OptionCard } from "../../components/OptionCard";
import {
  FORMS,
  INGREDIENTS,
  MASSES,
  NEXT_LABELS,
  PHOTOS,
  STEP_DESCRIPTIONS,
  STEP_HEADINGS,
  STEP_LABELS,
  TIME_SLOTS,
  WEEKDAYS,
} from "./catalog";
import { dateKey, isDayDisabled, monthStartLocked } from "./state";
import { useBreadBuilder } from "./useBreadBuilder";

export function BreadBuilder() {
  const builder = useBreadBuilder();
  const {
    state,
    earliest,
    selectMass,
    toggleIngredient,
    selectShape,
    selectDate,
    selectTime,
    shiftMonth,
    next,
    back,
    restart,
    canFinish,
    tip,
    formTip,
    summary,
    receipt,
  } = builder;
  const contentRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    contentRef.current?.focus();
  }, [state.step, state.finished]);

  const previewTitle =
    state.step === 0 && !state.finished ? (
      <>
        Simples na essência.
        <br />
        Extraordinário no sabor.
      </>
    ) : (
      MASSES[state.massIndex].title
    );

  const lastDay = new Date(state.month.getFullYear(), state.month.getMonth() + 1, 0).getDate();
  const leadingBlanks = state.month.getDay();
  const days: Array<Date | null> = [
    ...Array.from({ length: leadingBlanks }, () => null),
    ...Array.from({ length: lastDay }, (_, index) => new Date(state.month.getFullYear(), state.month.getMonth(), index + 1)),
  ];

  return (
    <section id="criacao" className="studio" aria-label="Assistente de criação">
      <div className="workspace">
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
          {state.finished ? (
            <div className="success">
              <div className="success-mark">✓</div>
              <p className="step-eyebrow">SUA COMBINAÇÃO ESTÁ PRONTA</p>
              <h2>Uma boa história para assar.</h2>
              <p className="desc">Você criou um pão com o seu toque. Guarde esta inspiração para a próxima fornada.</p>
              <div className="receipt">
                <strong>{receipt[0]}</strong>
                <br />
                {receipt[1]}
                <br />
                {receipt[2]}
                <br />
                {receipt[3]}
              </div>
              <p className="demo">
                Esta é uma simulação. Nenhum pedido foi enviado, cobrado ou agendado. Os horários são ilustrativos.
              </p>
              <button id="restart" className="text-button" type="button" onClick={restart}>
                Criar outra combinação →
              </button>
            </div>
          ) : (
            <>
              <p className="step-eyebrow">PASSO 0{state.step + 1}</p>
              <h2>{STEP_HEADINGS[state.step]}</h2>
              <p className="desc">{STEP_DESCRIPTIONS[state.step]}</p>
              {state.step === 0 ? (
                <div className="options">
                  {MASSES.map((mass, index) => (
                    <OptionCard
                      key={mass.title}
                      title={mass.title}
                      description={mass.description}
                      tag={state.massIndex === index ? mass.tag : ""}
                      selected={state.massIndex === index}
                      onSelect={() => selectMass(index)}
                    />
                  ))}
                </div>
              ) : null}
              {state.step === 1 ? (
                <>
                  <div className="ingredient-grid">
                    {INGREDIENTS.map((ingredient) => (
                      <OptionCard
                        key={ingredient.name}
                        title={ingredient.name}
                        description={ingredient.description}
                        selected={state.extras.includes(ingredient.name)}
                        onSelect={() => toggleIngredient(ingredient.name)}
                      />
                    ))}
                  </div>
                  <div className="tip" aria-live="polite">
                    <strong>Dica do padeiro</strong>
                    <br />
                    {tip}
                  </div>
                  <p className="demo">
                    Contém glúten. Nozes são oleaginosas. Informações sobre alergênicos precisam ser confirmadas pela
                    padaria.
                  </p>
                </>
              ) : null}
              {state.step === 2 ? (
                <>
                  <div className="options">
                    {FORMS.map((form, index) => (
                      <OptionCard
                        key={form.title}
                        title={form.title}
                        description={form.description}
                        selected={state.shapeIndex === index}
                        onSelect={() => selectShape(index)}
                      />
                    ))}
                  </div>
                  <div className="tip">{formTip}</div>
                </>
              ) : null}
              {state.step === 3 ? (
                <>
                  <div className="calendar-head">
                    <button
                      type="button"
                      aria-label="Mês anterior"
                      disabled={monthStartLocked(state.month, earliest)}
                      onClick={() => shiftMonth(-1)}
                    >
                      ‹
                    </button>
                    <strong>
                      {state.month.toLocaleDateString("pt-BR", { month: "long", year: "numeric" })}
                    </strong>
                    <button type="button" aria-label="Próximo mês" onClick={() => shiftMonth(1)}>
                      ›
                    </button>
                  </div>
                  <div className="calendar">
                    {WEEKDAYS.map((day, index) => (
                      <span key={`${day}-${index}`}>{day}</span>
                    ))}
                    {days.map((day, index) =>
                      day ? (
                        <button
                          key={dateKey(day)}
                          className={`day ${state.date === dateKey(day) ? "selected" : ""}`}
                          type="button"
                          disabled={isDayDisabled(day, earliest)}
                          aria-pressed={state.date === dateKey(day)}
                          aria-label={day.toLocaleDateString("pt-BR", {
                            day: "numeric",
                            month: "long",
                            year: "numeric",
                          })}
                          onClick={() => selectDate(dateKey(day))}
                        >
                          {day.getDate()}
                        </button>
                      ) : (
                        <span key={`blank-${index}`} />
                      ),
                    )}
                  </div>
                  <div className="times" aria-label="Horário de recebimento">
                    {TIME_SLOTS.map((slot) => (
                      <button
                        key={slot}
                        className={`time ${state.time === slot ? "selected" : ""}`}
                        type="button"
                        aria-pressed={state.time === slot}
                        onClick={() => selectTime(slot)}
                      >
                        {slot}
                      </button>
                    ))}
                  </div>
                  <p className="demo">
                    Calendário demonstrativo, com pelo menos dois dias para o preparo. Disponibilidade e entrega ainda
                    não estão conectadas à padaria.
                  </p>
                </>
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
          <button
            id="next"
            className="primary"
            type="button"
            onClick={next}
            hidden={state.finished}
            disabled={state.step === 3 && !canFinish}
          >
            {NEXT_LABELS[state.step]} <span>→</span>
          </button>
        </div>
      </div>
      <aside className="bread-preview">
        <div className="preview-photo">
          <img src={PHOTOS.panelHero.src} alt={PHOTOS.panelHero.alt} />
        </div>
        <div
          className="preview-board"
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
