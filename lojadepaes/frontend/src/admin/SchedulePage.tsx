import { useEffect, useState } from "react";
import { AdminApiError, adminRequest } from "./api";
import { DateRequestsPanel } from "./DateRequestsPanel";
import { WeekdayPicker } from "./WeekdayPicker";
import "./agenda.css";

type LinkedProduct = { id: string; name: string };
type RecipeBase = {
  id: string;
  code: string;
  name: string;
  is_active: boolean;
  products?: LinkedProduct[];
};
type DoughType = { id: string; name: string; code: string; recipe_base_id: string | null };
type Defaults = {
  production_weekdays: number[];
  daily_physical_limit: number;
  daily_base_limit: number;
  horizon_days: number;
  min_advance_hours: number;
  eligibility_mode: "inherit" | "explicit";
  eligible_base_ids: string[];
  reservation_policy: string;
};
type DayView = {
  date: string;
  week_start: string;
  week_end: string;
  origin: string;
  is_open: boolean;
  daily_physical_limit: number;
  daily_base_limit: number;
  committed_physical: number;
  committed_base_ids: string[];
};
type WeekPreview = {
  week_start: string;
  week_end: string;
  conflicts: string[];
  dates: Array<{
    date: string;
    origin: string;
    is_open: boolean;
    daily_physical_limit: number;
    daily_base_limit: number;
    committed_physical: number;
    conflicts: string[];
  }>;
};
type Notice = { tone: "saving" | "success" | "error"; text: string } | null;
type DayMode = "inherit" | "explicit";
type LimitMode = "inherit" | "replace";

function toggleId(current: string[], id: string): string[] {
  return current.includes(id) ? current.filter((item) => item !== id) : [...current, id];
}

function message(reason: unknown, fallback: string): string {
  return reason instanceof AdminApiError ? reason.message : fallback;
}

function optionalLimit(raw: string): number | null {
  if (raw.trim() === "") {
    return null;
  }
  const value = Number(raw);
  return Number.isFinite(value) ? value : null;
}

function keepInt(raw: string, current: number): number {
  if (raw.trim() === "") {
    return current;
  }
  const value = Number(raw);
  return Number.isInteger(value) ? value : current;
}

function originLabel(origin: string): string {
  if (origin === "date") {
    return "ajuste da data";
  }
  if (origin === "week") {
    return "ajuste da semana";
  }
  return "rotina";
}

function countWord(amount: number, singular: string, plural: string): string {
  return `${amount} ${amount === 1 ? singular : plural}`;
}

function effectiveLimitNote(view: DayView | null, kind: "bread" | "type"): string {
  if (!view) {
    return "Em branco, esta data não grava um número próprio. Consulte a data para ver o que vale agora.";
  }
  const amount = kind === "bread" ? view.daily_physical_limit : view.daily_base_limit;
  const label = kind === "bread" ? countWord(amount, "pão", "pães") : countWord(amount, "tipo", "tipos");
  return `Em branco, esta data não grava um número próprio. Agora valem ${label}, pela origem ${originLabel(view.origin)}.`;
}

function suggestCode(name: string, taken: Set<string>): string {
  const normalized = name.normalize("NFD").replace(/[\u0300-\u036f]/g, "");
  const base = normalized
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 40)
    .toUpperCase();
  if (!base || !taken.has(base)) {
    return base;
  }
  for (let index = 2; index < 100; index += 1) {
    const suffix = `-${index}`;
    const candidate = `${base.slice(0, 40 - suffix.length)}${suffix}`;
    if (!taken.has(candidate)) {
      return candidate;
    }
  }
  return "";
}

function NoticeLine({ notice }: { notice: Notice }) {
  if (!notice) {
    return null;
  }
  if (notice.tone === "error") {
    return (
      <p className="admin-error" role="alert">
        {notice.text}
      </p>
    );
  }
  if (notice.tone === "success") {
    return <p className="admin-success">{notice.text}</p>;
  }
  return <p className="admin-muted">{notice.text}</p>;
}

function BaseChoices({
  bases,
  selected,
  onToggle,
}: {
  bases: RecipeBase[];
  selected: string[];
  onToggle: (id: string) => void;
}) {
  const active = bases.filter((base) => base.is_active);
  if (active.length === 0) {
    return <p className="agenda-help">Nenhum tipo de pão ativo.</p>;
  }
  return (
    <div className="agenda-choices">
      {active.map((base) => (
        <label key={base.id} className="agenda-choice">
          <input
            type="checkbox"
            checked={selected.includes(base.id)}
            onChange={() => onToggle(base.id)}
          />
          {base.name}
        </label>
      ))}
    </div>
  );
}

function LimitField({
  label,
  value,
  mode,
  onMode,
  onChange,
  followingNote,
}: {
  label: string;
  value: string;
  mode: LimitMode;
  onMode: (mode: LimitMode) => void;
  onChange: (value: string) => void;
  followingNote: string;
}) {
  const replacing = mode === "replace";
  let note = followingNote;
  if (replacing && value.trim() === "") {
    note = "Digite o número para substituir o padrão. Vazio continua seguindo o padrão. Zero é um limite próprio.";
  } else if (replacing && value === "0") {
    note = "Zero é um limite próprio, diferente de seguir o padrão.";
  } else if (replacing) {
    note = "Este número substitui o padrão e só vale depois de salvar.";
  }
  return (
    <div className="agenda-limit">
      <p className="agenda-limit-label">{label}</p>
      <div className="agenda-mode" role="group" aria-label={label}>
        <button
          type="button"
          aria-pressed={!replacing}
          onClick={() => {
            onMode("inherit");
            onChange("");
          }}
        >
          Seguir o padrão
        </button>
        <button type="button" aria-pressed={replacing} onClick={() => onMode("replace")}>
          Substituir
        </button>
      </div>
      {replacing ? (
        <label className="agenda-field agenda-field-narrow">
          Número
          <input
            inputMode="numeric"
            value={value}
            onChange={(event) => onChange(event.target.value.replace(/\D/g, ""))}
          />
        </label>
      ) : null}
      <p className="agenda-help">{note}</p>
    </div>
  );
}

export function SchedulePage() {
  const [defaults, setDefaults] = useState<Defaults | null>(null);
  const [bases, setBases] = useState<RecipeBase[]>([]);
  const [doughs, setDoughs] = useState<DoughType[]>([]);
  const [day, setDay] = useState("");
  const [dayView, setDayView] = useState<DayView | null>(null);
  const [weekStart, setWeekStart] = useState("");
  const [weekPreview, setWeekPreview] = useState<WeekPreview | null>(null);
  const [weekPhysical, setWeekPhysical] = useState("");
  const [weekBases, setWeekBases] = useState("");
  const [weekPhysicalMode, setWeekPhysicalMode] = useState<LimitMode>("inherit");
  const [weekBaseMode, setWeekBaseMode] = useState<LimitMode>("inherit");
  const [weekDaysMode, setWeekDaysMode] = useState<DayMode>("inherit");
  const [weekDays, setWeekDays] = useState<number[]>([]);
  const [dateOpen, setDateOpen] = useState<"inherit" | "open" | "closed">("inherit");
  const [datePhysical, setDatePhysical] = useState("");
  const [dateBases, setDateBases] = useState("");
  const [datePhysicalMode, setDatePhysicalMode] = useState<LimitMode>("inherit");
  const [dateBaseMode, setDateBaseMode] = useState<LimitMode>("inherit");
  const [weekEligibility, setWeekEligibility] = useState<"inherit" | "explicit">("inherit");
  const [weekEligibleIds, setWeekEligibleIds] = useState<string[]>([]);
  const [dateEligibility, setDateEligibility] = useState<"inherit" | "explicit">("inherit");
  const [dateEligibleIds, setDateEligibleIds] = useState<string[]>([]);
  const [newBaseCode, setNewBaseCode] = useState("");
  const [newBaseName, setNewBaseName] = useState("");
  const [codeTouched, setCodeTouched] = useState(false);
  const [typesOpen, setTypesOpen] = useState(false);
  const [routineNotice, setRoutineNotice] = useState<Notice>(null);
  const [weekNotice, setWeekNotice] = useState<Notice>(null);
  const [dateNotice, setDateNotice] = useState<Notice>(null);
  const [baseNotice, setBaseNotice] = useState<Notice>(null);
  const [loadError, setLoadError] = useState<string | null>(null);

  async function reload() {
    const [schedule, recipeBases, doughTypes] = await Promise.all([
      adminRequest<Defaults>("/api/v1/admin/schedule"),
      adminRequest<RecipeBase[]>("/api/v1/admin/recipe-bases"),
      adminRequest<DoughType[]>("/api/v1/admin/dough-types"),
    ]);
    setDefaults({ ...schedule, eligible_base_ids: schedule.eligible_base_ids ?? [] });
    setBases(recipeBases);
    setDoughs(doughTypes);
  }

  useEffect(() => {
    reload().catch((reason: unknown) => {
      setLoadError(message(reason, "Não foi possível abrir a agenda."));
    });
  }, []);

  function weekPayload() {
    return {
      week_start: weekStart,
      production_weekdays: weekDaysMode === "inherit" ? null : weekDays,
      daily_physical_limit: weekPhysicalMode === "inherit" ? null : optionalLimit(weekPhysical),
      daily_base_limit: weekBaseMode === "inherit" ? null : optionalLimit(weekBases),
      eligibility_mode: weekEligibility,
      eligible_base_ids: weekEligibility === "explicit" ? weekEligibleIds : null,
    };
  }

  async function saveDefaults() {
    if (!defaults) {
      return;
    }
    setRoutineNotice({ tone: "saving", text: "Salvando…" });
    try {
      const saved = await adminRequest<Defaults>("/api/v1/admin/schedule", {
        method: "PUT",
        body: JSON.stringify({
          ...defaults,
          eligible_base_ids: defaults.eligibility_mode === "explicit" ? defaults.eligible_base_ids : null,
        }),
      });
      setDefaults({ ...saved, eligible_base_ids: saved.eligible_base_ids ?? [] });
      setRoutineNotice({ tone: "success", text: "Rotina salva." });
    } catch (reason) {
      setRoutineNotice({ tone: "error", text: message(reason, "Não foi possível salvar a rotina.") });
    }
  }

  async function inspectDay() {
    if (!day) {
      setDateNotice({ tone: "error", text: "Informe a data." });
      return;
    }
    setDateNotice(null);
    try {
      const view = await adminRequest<DayView>(`/api/v1/admin/schedule/days/${day}`);
      setDayView(view);
    } catch (reason) {
      setDateNotice({ tone: "error", text: message(reason, "Não foi possível consultar a data.") });
    }
  }

  async function previewWeek() {
    if (!weekStart) {
      setWeekNotice({ tone: "error", text: "Informe a semana." });
      return;
    }
    setWeekNotice(null);
    try {
      const preview = await adminRequest<WeekPreview>("/api/v1/admin/schedule/weeks/preview", {
        method: "POST",
        body: JSON.stringify(weekPayload()),
      });
      setWeekPreview(preview);
    } catch (reason) {
      setWeekNotice({ tone: "error", text: message(reason, "Não foi possível consultar a semana.") });
    }
  }

  async function saveWeek() {
    if (!weekStart) {
      setWeekNotice({ tone: "error", text: "Informe a semana." });
      return;
    }
    setWeekNotice({ tone: "saving", text: "Salvando…" });
    try {
      await adminRequest("/api/v1/admin/schedule/weeks", {
        method: "PUT",
        body: JSON.stringify(weekPayload()),
      });
      setWeekNotice({ tone: "success", text: "Semana salva." });
      const preview = await adminRequest<WeekPreview>("/api/v1/admin/schedule/weeks/preview", {
        method: "POST",
        body: JSON.stringify(weekPayload()),
      });
      setWeekPreview(preview);
    } catch (reason) {
      setWeekNotice({ tone: "error", text: message(reason, "Não foi possível salvar a semana.") });
    }
  }

  async function removeWeek() {
    if (!weekStart) {
      setWeekNotice({ tone: "error", text: "Informe a semana." });
      return;
    }
    setWeekNotice({ tone: "saving", text: "Salvando…" });
    try {
      await adminRequest(`/api/v1/admin/schedule/weeks/${weekStart}`, { method: "DELETE" });
      setWeekPreview(null);
      setWeekDaysMode("inherit");
      setWeekDays([]);
      setWeekPhysical("");
      setWeekBases("");
      setWeekPhysicalMode("inherit");
      setWeekBaseMode("inherit");
      setWeekEligibility("inherit");
      setWeekEligibleIds([]);
      setWeekNotice({ tone: "success", text: "A semana voltou a usar a rotina." });
    } catch (reason) {
      setWeekNotice({ tone: "error", text: message(reason, "Não foi possível remover a exceção.") });
    }
  }

  async function saveDate() {
    if (!day) {
      setDateNotice({ tone: "error", text: "Informe a data." });
      return;
    }
    setDateNotice({ tone: "saving", text: "Salvando…" });
    try {
      await adminRequest("/api/v1/admin/schedule/dates", {
        method: "PUT",
        body: JSON.stringify({
          local_date: day,
          open_state: dateOpen,
          daily_physical_limit: datePhysicalMode === "inherit" ? null : optionalLimit(datePhysical),
          daily_base_limit: dateBaseMode === "inherit" ? null : optionalLimit(dateBases),
          eligibility_mode: dateEligibility,
          eligible_base_ids: dateEligibility === "explicit" ? dateEligibleIds : null,
        }),
      });
      setDateNotice({ tone: "success", text: "Data salva." });
      const view = await adminRequest<DayView>(`/api/v1/admin/schedule/days/${day}`);
      setDayView(view);
    } catch (reason) {
      setDateNotice({ tone: "error", text: message(reason, "Não foi possível salvar a data.") });
    }
  }

  async function removeDate() {
    if (!day) {
      setDateNotice({ tone: "error", text: "Informe a data." });
      return;
    }
    setDateNotice({ tone: "saving", text: "Salvando…" });
    try {
      await adminRequest(`/api/v1/admin/schedule/dates/${day}`, { method: "DELETE" });
      setDateOpen("inherit");
      setDatePhysical("");
      setDateBases("");
      setDatePhysicalMode("inherit");
      setDateBaseMode("inherit");
      setDateEligibility("inherit");
      setDateEligibleIds([]);
      setDateNotice({ tone: "success", text: "A data voltou a usar a configuração herdada." });
      const view = await adminRequest<DayView>(`/api/v1/admin/schedule/days/${day}`);
      setDayView(view);
    } catch (reason) {
      setDateNotice({ tone: "error", text: message(reason, "Não foi possível remover a exceção.") });
    }
  }

  async function createBase() {
    setBaseNotice({ tone: "saving", text: "Salvando…" });
    try {
      await adminRequest("/api/v1/admin/recipe-bases", {
        method: "POST",
        body: JSON.stringify({ code: newBaseCode, name: newBaseName }),
      });
      setNewBaseCode("");
      setNewBaseName("");
      setCodeTouched(false);
      await reload();
      setBaseNotice({ tone: "success", text: "Tipo de pão adicionado." });
    } catch (reason) {
      setBaseNotice({ tone: "error", text: message(reason, "Não foi possível criar o agrupamento.") });
    }
  }

  if (!defaults) {
    return loadError ? <p className="admin-error">{loadError}</p> : <p className="admin-muted">Carregando agenda…</p>;
  }

  return (
    <section className="admin-page agenda-page">
      <header className="admin-page-head">
        <div>
          <p className="admin-eyebrow">Produção</p>
          <h1>Agenda de fornadas</h1>
          <p className="admin-lead">Defina os dias e a capacidade de cada fornada.</p>
        </div>
      </header>

      <article className="agenda-card">
        <div>
          <h2>Rotina da padaria</h2>
          <p className="agenda-help">Os quatro blocos abaixo formam a rotina.</p>
        </div>
        <div className="agenda-routine-grid">
          <div className="agenda-block agenda-block-days">
            <h3>Dias de produção</h3>
            <WeekdayPicker
              selected={defaults.production_weekdays}
              onChange={(next) => setDefaults({ ...defaults, production_weekdays: next })}
            />
          </div>
          <div className="agenda-block agenda-block-capacity">
            <h3>Capacidade da fornada</h3>
            <div className="agenda-fields">
              <label className="agenda-field">
                Pães por dia
                <input
                  inputMode="numeric"
                  value={defaults.daily_physical_limit}
                  onChange={(event) =>
                    setDefaults({
                      ...defaults,
                      daily_physical_limit: keepInt(event.target.value, defaults.daily_physical_limit),
                    })
                  }
                />
              </label>
              <label className="agenda-field">
                Tipos de pão por dia
                <input
                  inputMode="numeric"
                  aria-describedby="agenda-base-help"
                  value={defaults.daily_base_limit}
                  onChange={(event) =>
                    setDefaults({
                      ...defaults,
                      daily_base_limit: keepInt(event.target.value, defaults.daily_base_limit),
                    })
                  }
                />
              </label>
            </div>
            <p className="agenda-help" id="agenda-base-help">
              Quantas receitas-base diferentes podemos produzir no mesmo dia.
            </p>
          </div>
          <div className="agenda-block agenda-block-lead">
            <h3>Prazo para encomendar</h3>
            <div className="agenda-fields">
              <label className="agenda-field">
                Mostrar datas dos próximos (dias)
                <input
                  inputMode="numeric"
                  aria-describedby="agenda-horizon-help"
                  value={defaults.horizon_days}
                  onChange={(event) =>
                    setDefaults({ ...defaults, horizon_days: keepInt(event.target.value, defaults.horizon_days) })
                  }
                />
              </label>
              <label className="agenda-field">
                Prazo mínimo antes da fornada (horas)
                <input
                  inputMode="numeric"
                  aria-describedby="agenda-advance-help"
                  value={defaults.min_advance_hours}
                  onChange={(event) =>
                    setDefaults({
                      ...defaults,
                      min_advance_hours: keepInt(event.target.value, defaults.min_advance_hours),
                    })
                  }
                />
              </label>
            </div>
            <p className="agenda-help" id="agenda-horizon-help">
              Até quantos dias à frente o cliente pode escolher uma fornada.
            </p>
            <p className="agenda-help" id="agenda-advance-help">
              Somamos essas horas ao horário de agora e olhamos só a data que resulta. Se essa data já passou da
              fornada, o dia não entra na escolha. Não é um horário fixo de corte.
            </p>
          </div>
          <div className="agenda-block agenda-block-types">
            <h3>Tipos de pão oferecidos</h3>
            <p className="agenda-help">
              A lista define quais tipos o cliente pode pedir. O número de tipos por dia define quantos cabem na mesma
              fornada.
            </p>
            <label className="agenda-field">
              Quais tipos entram
              <select
                value={defaults.eligibility_mode}
                onChange={(event) =>
                  setDefaults({
                    ...defaults,
                    eligibility_mode: event.target.value as Defaults["eligibility_mode"],
                  })
                }
              >
                <option value="inherit">Todos os tipos ativos</option>
                <option value="explicit">Escolher os tipos</option>
              </select>
            </label>
            {defaults.eligibility_mode === "explicit" ? (
              <BaseChoices
                bases={bases}
                selected={defaults.eligible_base_ids}
                onToggle={(id) =>
                  setDefaults({ ...defaults, eligible_base_ids: toggleId(defaults.eligible_base_ids, id) })
                }
              />
            ) : null}
          </div>
        </div>
        <div className="agenda-savebar">
          <button
            type="button"
            className="admin-primary"
            disabled={routineNotice?.tone === "saving"}
            onClick={() => void saveDefaults()}
          >
            Salvar rotina
          </button>
          <p className="agenda-help">Salva os quatro blocos juntos.</p>
          <NoticeLine notice={routineNotice} />
        </div>
      </article>

      <p className="agenda-priority">
        O ajuste do dia vale primeiro. Depois, o da semana. Sem ajustes, vale a rotina.
      </p>
      <div className="agenda-pair">
        <article className="agenda-card agenda-card-week">
          <div>
            <h2>Ajustar uma semana</h2>
            <p className="agenda-help">Mude os dias ou a capacidade somente nesta semana.</p>
            <NoticeLine notice={weekNotice} />
          </div>
          <div className="agenda-section">
            <h3>Período</h3>
            <label className="agenda-field">
              Início da semana
              <input type="date" value={weekStart} onChange={(event) => setWeekStart(event.target.value)} />
            </label>
          </div>
          <div className="agenda-section">
            <h3>Dias de produção</h3>
            <div className="agenda-mode" role="group" aria-label="Origem dos dias da semana">
              <button
                type="button"
                aria-pressed={weekDaysMode === "inherit"}
                onClick={() => setWeekDaysMode("inherit")}
              >
                Usar a rotina
              </button>
              <button
                type="button"
                aria-pressed={weekDaysMode === "explicit"}
                onClick={() => setWeekDaysMode("explicit")}
              >
                Escolher os dias
              </button>
            </div>
            <WeekdayPicker
              selected={weekDaysMode === "explicit" ? weekDays : []}
              disabled={weekDaysMode !== "explicit"}
              onChange={setWeekDays}
            />
            <p className="agenda-help">
              {weekDaysMode === "inherit"
                ? "Os dias desta semana seguem a rotina."
                : "Nenhum dia marcado vale como semana sem produção. Isso não volta sozinho para a rotina."}
            </p>
          </div>
          <div className="agenda-section">
            <h3>Limites</h3>
            <LimitField
              label="Pães por dia"
              value={weekPhysical}
              mode={weekPhysicalMode}
              onMode={setWeekPhysicalMode}
              onChange={setWeekPhysical}
              followingNote={`Segue a rotina: ${countWord(defaults.daily_physical_limit, "pão", "pães")}`}
            />
            <LimitField
              label="Tipos de pão por dia"
              value={weekBases}
              mode={weekBaseMode}
              onMode={setWeekBaseMode}
              onChange={setWeekBases}
              followingNote={`Segue a rotina: ${countWord(defaults.daily_base_limit, "tipo", "tipos")}`}
            />
          </div>
          <div className="agenda-section">
            <h3>Tipos oferecidos</h3>
            <p className="agenda-help">Sem lista própria, vale a rotina.</p>
            <label className="agenda-field">
              Quais tipos entram
              <select
                value={weekEligibility}
                onChange={(event) => setWeekEligibility(event.target.value as typeof weekEligibility)}
              >
                <option value="inherit">Seguir a rotina</option>
                <option value="explicit">Escolher nesta semana</option>
              </select>
            </label>
            {weekEligibility === "explicit" ? (
              <BaseChoices
                bases={bases}
                selected={weekEligibleIds}
                onToggle={(id) => setWeekEligibleIds((current) => toggleId(current, id))}
              />
            ) : null}
          </div>
          <div className="agenda-footer">
            <div className="agenda-actions">
              <button type="button" className="admin-secondary" onClick={() => void previewWeek()}>
                Ver datas afetadas
              </button>
              <button
                type="button"
                className="admin-primary"
                disabled={weekNotice?.tone === "saving"}
                onClick={() => void saveWeek()}
              >
                Salvar semana
              </button>
            </div>
            <div className="agenda-remove-row">
              <button
                type="button"
                className="admin-text"
                disabled={weekNotice?.tone === "saving"}
                onClick={() => void removeWeek()}
              >
                Remover exceção
              </button>
              <p className="agenda-help">Remove o ajuste desta semana e volta a valer a configuração anterior.</p>
            </div>
          </div>
          {weekPreview ? (
            <ul className="agenda-preview">
              {weekPreview.dates.map((item) => (
                <li key={item.date}>
                  {item.date}: {item.is_open ? "aberta" : "fechada"}, {originLabel(item.origin)},{" "}
                  {item.daily_physical_limit} pães, {item.daily_base_limit} tipos
                  {item.conflicts.length ? `. ${item.conflicts.join(" ")}` : ""}
                </li>
              ))}
            </ul>
          ) : null}
        </article>

        <article className="agenda-card agenda-card-date">
          <div>
            <h2>Ajustar uma data</h2>
            <p className="agenda-help">Abra, feche ou ajuste uma fornada em um dia específico.</p>
            <NoticeLine notice={dateNotice} />
          </div>
          <div className="agenda-section">
            <h3>Data</h3>
            <label className="agenda-field">
              Data
              <input type="date" value={day} onChange={(event) => setDay(event.target.value)} />
            </label>
          </div>
          <div className="agenda-section">
            <h3>Abertura</h3>
            <label className="agenda-field">
              Este dia
              <select value={dateOpen} onChange={(event) => setDateOpen(event.target.value as typeof dateOpen)}>
                <option value="inherit">Seguir o padrão</option>
                <option value="open">Abrir</option>
                <option value="closed">Fechar</option>
              </select>
            </label>
            <p className="agenda-help">Sem ajuste próprio, o dia segue a semana ou a rotina.</p>
          </div>
          <div className="agenda-section">
            <h3>Limites</h3>
            <LimitField
              label="Pães por dia"
              value={datePhysical}
              mode={datePhysicalMode}
              onMode={setDatePhysicalMode}
              onChange={setDatePhysical}
              followingNote={effectiveLimitNote(dayView, "bread")}
            />
            <LimitField
              label="Tipos de pão por dia"
              value={dateBases}
              mode={dateBaseMode}
              onMode={setDateBaseMode}
              onChange={setDateBases}
              followingNote={effectiveLimitNote(dayView, "type")}
            />
          </div>
          <div className="agenda-section">
            <h3>Tipos oferecidos</h3>
            <p className="agenda-help">Sem lista própria, vale a semana ou a rotina.</p>
            <label className="agenda-field">
              Quais tipos entram
              <select
                value={dateEligibility}
                onChange={(event) => setDateEligibility(event.target.value as typeof dateEligibility)}
              >
                <option value="inherit">Seguir o padrão</option>
                <option value="explicit">Escolher neste dia</option>
              </select>
            </label>
            {dateEligibility === "explicit" ? (
              <BaseChoices
                bases={bases}
                selected={dateEligibleIds}
                onToggle={(id) => setDateEligibleIds((current) => toggleId(current, id))}
              />
            ) : null}
          </div>
          <div className="agenda-footer">
            <div className="agenda-actions">
              <button type="button" className="admin-secondary" onClick={() => void inspectDay()}>
                Ver configuração efetiva
              </button>
              <button
                type="button"
                className="admin-primary"
                disabled={dateNotice?.tone === "saving"}
                onClick={() => void saveDate()}
              >
                Salvar data
              </button>
            </div>
            <div className="agenda-remove-row">
              <button
                type="button"
                className="admin-text"
                disabled={dateNotice?.tone === "saving"}
                onClick={() => void removeDate()}
              >
                Remover exceção
              </button>
              <p className="agenda-help">Remove o ajuste deste dia e volta a valer a configuração anterior.</p>
            </div>
          </div>
          {dayView ? (
            <p className="admin-lead">
              {dayView.date}: {dayView.is_open ? "aberta" : "fechada"}, origem {originLabel(dayView.origin)},{" "}
              {dayView.daily_physical_limit} pães, {dayView.daily_base_limit} tipos, {dayView.committed_physical} já
              comprometidos. Semana {dayView.week_start} a {dayView.week_end}.
            </p>
          ) : null}
        </article>
      </div>

      <article className="agenda-card agenda-card-types">
        <div>
          <h2>Tipos de pão para organizar as fornadas</h2>
          <p className="agenda-help">
            Aqui você organiza os pães pela receita-base usada na produção. Isso permite controlar quantos tipos
            diferentes entram em cada fornada.
          </p>
          <div className="agenda-example">
            <p className="agenda-example-label">Exemplo</p>
            <p>
              Um pão de limão de 500 g e outro de 800 g podem usar a mesma receita-base e contar como um único tipo.
              Receitas-base diferentes contam como tipos diferentes. Inclusões não criam um novo tipo.
            </p>
          </div>
          <p className="agenda-help">
            Cadastre o tipo aqui, vincule-o ao produto na configuração de produção do editor e use-o na agenda. Isso
            não é a receita completa, a descrição comercial nem a rotulagem. A integração com o Panne continua para
            outra etapa.
          </p>
          <p className="agenda-summary">
            {bases.length === 0
              ? "Nenhum tipo cadastrado."
              : bases.length === 1
                ? "1 tipo cadastrado."
                : `${bases.length} tipos cadastrados.`}
          </p>
          <button
            type="button"
            className="admin-secondary"
            aria-expanded={typesOpen}
            aria-controls="agenda-types-panel"
            onClick={() => setTypesOpen((open) => !open)}
          >
            Gerenciar tipos de pão
          </button>
        </div>
        {typesOpen ? (
          <div id="agenda-types-panel" className="agenda-types-panel">
            <NoticeLine notice={baseNotice} />
            {bases.length > 0 ? (
              <ul className="agenda-type-list">
                {bases.map((base) => (
                  <li key={base.id} className="agenda-type">
                    <p className="agenda-type-name">
                      {base.name}
                      {base.is_active ? "" : " (inativo)"}
                    </p>
                    <p className="agenda-type-code">Código interno {base.code}</p>
                    {"products" in base ? (
                      base.products && base.products.length > 0 ? (
                        <p className="agenda-help">
                          Pães com este tipo:{" "}
                          {base.products.map((product, index) => (
                            <span key={product.id}>
                              {index > 0 ? ", " : ""}
                              <a className="admin-link" href={`/admin/produtos/${product.id}`}>
                                {product.name}
                              </a>
                            </span>
                          ))}
                        </p>
                      ) : (
                        <p className="agenda-help">Nenhum pão vinculado a este tipo.</p>
                      )
                    ) : (
                      <p className="agenda-help">
                        O vínculo de cada pão fica na configuração de produção do editor.
                      </p>
                    )}
                  </li>
                ))}
              </ul>
            ) : (
              <p className="agenda-help">Nenhum tipo cadastrado ainda.</p>
            )}
            <div className="agenda-section">
              <h3>Novo tipo</h3>
              <div className="agenda-fields">
                <label className="agenda-field">
                  Nome do tipo de pão
                  <input
                    value={newBaseName}
                    onChange={(event) => {
                      const nextName = event.target.value;
                      setNewBaseName(nextName);
                      if (!codeTouched) {
                        const taken = new Set(bases.map((base) => base.code.toUpperCase()));
                        setNewBaseCode(suggestCode(nextName, taken));
                      }
                    }}
                  />
                </label>
                <label className="agenda-field">
                  Código interno
                  <input
                    value={newBaseCode}
                    aria-describedby="agenda-code-help"
                    onChange={(event) => {
                      setCodeTouched(true);
                      setNewBaseCode(event.target.value);
                    }}
                  />
                </label>
              </div>
              <p className="agenda-help" id="agenda-code-help">
                Referência estável da agenda. Não aparece para o cliente. O servidor recusa um código repetido e não
                altera códigos já salvos. A sugestão vale só para este cadastro novo.
              </p>
              <div className="agenda-actions">
                <button
                  type="button"
                  className="admin-secondary"
                  disabled={baseNotice?.tone === "saving"}
                  onClick={() => void createBase()}
                >
                  Adicionar tipo de pão
                </button>
              </div>
            </div>
            {doughs.length > 0 ? (
              <div className="agenda-section">
                <h3>Massas do assistente</h3>
                <p className="agenda-help">
                  Associe as massas do assistente a esses mesmos tipos para contar a produção em conjunto.
                </p>
                {doughs.map((dough) => (
                  <label key={dough.id} className="agenda-field">
                    {dough.name}
                    <select
                      aria-label={`Tipo de pão da massa ${dough.name}`}
                      value={dough.recipe_base_id ?? ""}
                      onChange={(event) => {
                        const recipeBaseId = event.target.value || null;
                        void adminRequest(`/api/v1/admin/dough-types/${dough.id}/recipe-base`, {
                          method: "PUT",
                          body: JSON.stringify({ recipe_base_id: recipeBaseId }),
                        })
                          .then(() => reload())
                          .catch((reason: unknown) => {
                            setBaseNotice({
                              tone: "error",
                              text: message(reason, "Não foi possível vincular a massa."),
                            });
                          });
                      }}
                    >
                      <option value="">Sem vínculo</option>
                      {bases
                        .filter((base) => base.is_active)
                        .map((base) => (
                          <option key={base.id} value={base.id}>
                            {base.name}
                          </option>
                        ))}
                    </select>
                  </label>
                ))}
              </div>
            ) : null}
          </div>
        ) : null}
      </article>

      <DateRequestsPanel />
    </section>
  );
}
