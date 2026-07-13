import { useEffect, useMemo, useState } from 'react';
import {
  ROLE_PO,
  ROLE_SM,
  SQUAD_MAX_SPECIALISTS,
  professionalRoleLabel,
} from '../../constants/capacity';
import {
  getTdSprintSquad,
  listProfessionals,
  saveTdSprintSquad,
} from '../../services/tdApi';

/**
 * Montagem 1:1 da Squad (Task Force) dedicada à sprint.
 */
export default function TdSprintSquadSection({
  sprintId,
  initialSquad = null,
  onSaved,
  onError,
}) {
  const [professionals, setProfessionals] = useState([]);
  const [poId, setPoId] = useState(initialSquad?.po_id || '');
  const [smId, setSmId] = useState(initialSquad?.sm_id || '');
  const [memberIds, setMemberIds] = useState(initialSquad?.member_ids || []);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [localMsg, setLocalMsg] = useState('');

  useEffect(() => {
    let cancelled = false;
    async function load() {
      if (!sprintId) {
        setLoading(false);
        return;
      }
      setLoading(true);
      try {
        const [poolRes, squadRes] = await Promise.all([
          listProfessionals({ activeOnly: true }),
          getTdSprintSquad(sprintId),
        ]);
        if (cancelled) return;
        setProfessionals(poolRes.professionals || []);
        const squad = squadRes.squad || initialSquad;
        if (squad) {
          setPoId(squad.po_id || '');
          setSmId(squad.sm_id || '');
          setMemberIds(squad.member_ids || []);
        }
      } catch (err) {
        onError?.(err.message || 'Erro ao carregar pool / squad.');
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps -- carrega por sprintId
  }, [sprintId]);

  const pos = useMemo(
    () => professionals.filter((p) => p.role === ROLE_PO),
    [professionals],
  );
  const sms = useMemo(
    () => professionals.filter((p) => p.role === ROLE_SM),
    [professionals],
  );
  const specialists = useMemo(
    () =>
      professionals.filter(
        (p) => p.role !== ROLE_PO && p.role !== ROLE_SM && p.id !== poId && p.id !== smId,
      ),
    [professionals, poId, smId],
  );

  function toggleMember(id) {
    setMemberIds((prev) => {
      if (prev.includes(id)) return prev.filter((x) => x !== id);
      if (prev.length >= SQUAD_MAX_SPECIALISTS) {
        onError?.(
          `A equipe técnica pode ter no máximo ${SQUAD_MAX_SPECIALISTS} especialistas.`,
        );
        return prev;
      }
      return [...prev, id];
    });
  }

  async function handleSave() {
    if (!sprintId) return;
    setSaving(true);
    setLocalMsg('');
    try {
      const res = await saveTdSprintSquad(sprintId, {
        po_id: poId || null,
        sm_id: smId || null,
        member_ids: memberIds,
      });
      setLocalMsg('Squad salva com sucesso.');
      onSaved?.(res.squad);
    } catch (err) {
      const msg = err.message || 'Falha ao salvar a Squad.';
      onError?.(msg);
    } finally {
      setSaving(false);
    }
  }

  if (loading) {
    return (
      <section className="rounded-xl border border-chameleon/30 bg-chameleon/5 p-4">
        <p className="text-sm text-slate-600">Carregando formação da equipe…</p>
      </section>
    );
  }

  return (
    <section className="rounded-xl border border-chameleon/40 bg-gradient-to-br from-chameleon/10 to-white p-4">
      <header className="mb-3">
        <h3 className="text-sm font-black uppercase tracking-wide text-chameleon-dark">
          Formação da Equipe (Squad)
        </h3>
        <p className="mt-1 text-xs text-slate-600">
          Cada sprint tem uma Squad exclusiva (1:1). Constitui-se no{' '}
          <strong>planejamento</strong> e pode ser ajustada a qualquer momento na{' '}
          <strong>execução</strong>. Obrigatório: Product Owner e Scrum Master. Até{' '}
          {SQUAD_MAX_SPECIALISTS} especialistas · total máximo 8.
        </p>
      </header>

      {professionals.length === 0 ? (
        <p className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-900">
          Pool vazio. Cadastre profissionais em <strong>Gestão Operacional → Pool de Talentos</strong>.
        </p>
      ) : (
        <div className="space-y-3">
          <label className="block text-xs font-bold text-slate-700">
            Product Owner
            <select
              value={poId}
              onChange={(e) => setPoId(e.target.value)}
              className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm"
            >
              <option value="">Selecione o PO…</option>
              {pos.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name}
                </option>
              ))}
            </select>
            {pos.length === 0 && (
              <span className="mt-1 block text-[11px] font-normal text-amber-700">
                Nenhum profissional com cargo PO no pool.
              </span>
            )}
          </label>

          <label className="block text-xs font-bold text-slate-700">
            Scrum Master
            <select
              value={smId}
              onChange={(e) => setSmId(e.target.value)}
              className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm"
            >
              <option value="">Selecione o SM…</option>
              {sms.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name}
                </option>
              ))}
            </select>
            {sms.length === 0 && (
              <span className="mt-1 block text-[11px] font-normal text-amber-700">
                Nenhum profissional com cargo Scrum Master no pool.
              </span>
            )}
          </label>

          <div>
            <p className="text-xs font-bold text-slate-700">
              Equipe técnica ({memberIds.length}/{SQUAD_MAX_SPECIALISTS})
            </p>
            <div className="mt-2 max-h-40 space-y-1 overflow-y-auto rounded-lg border border-slate-200 bg-white p-2">
              {specialists.length === 0 && (
                <p className="px-1 py-2 text-[11px] text-slate-500">
                  Sem especialistas disponíveis no pool.
                </p>
              )}
              {specialists.map((p) => {
                const checked = memberIds.includes(p.id);
                return (
                  <label
                    key={p.id}
                    className={`flex cursor-pointer items-center gap-2 rounded-md px-2 py-1.5 text-sm hover:bg-slate-50 ${
                      checked ? 'bg-chameleon/10' : ''
                    }`}
                  >
                    <input
                      type="checkbox"
                      checked={checked}
                      onChange={() => toggleMember(p.id)}
                    />
                    <span className="font-medium text-slate-800">{p.name}</span>
                    <span className="text-[11px] text-slate-500">
                      {professionalRoleLabel(p.role)}
                    </span>
                  </label>
                );
              })}
            </div>
          </div>

          <button
            type="button"
            disabled={saving || !poId || !smId}
            onClick={handleSave}
            className="w-full rounded-lg bg-chameleon px-3 py-2 text-sm font-semibold text-white hover:bg-chameleon-dark disabled:opacity-50"
          >
            {saving ? 'Salvando Squad…' : 'Salvar / atualizar Squad desta sprint'}
          </button>
          {localMsg && (
            <p className="text-center text-xs font-medium text-emerald-700">{localMsg}</p>
          )}
        </div>
      )}
    </section>
  );
}
