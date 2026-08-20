import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { getOrganizationProfile, updateOrganizationProfile } from '../services/api';
import {
  createOrganizationalUnit,
  deleteOrganizationalUnit,
  listOrganizationalUnits,
  updateOrganizationalUnit,
} from '../services/organizationApi';
import { formatCnpj } from '../utils/documentMask';
import { getIndustryLabels } from '../utils/industryLabels';

const EMPTY_FORM = {
  employee_count: '',
  address: '',
  document: '',
};

const UNIT_TYPES = [
  { value: 'Filial', label: 'Filial' },
  { value: 'Escritorio', label: 'Escritório' },
  { value: 'Deposito', label: 'Depósito' },
  { value: 'Matriz', label: 'Matriz' },
  { value: 'Outro', label: 'Outro' },
];

const EMPTY_UNIT = {
  name: '',
  unit_type: 'Filial',
  address: '',
  responsible_name: '',
  responsible_email: '',
  responsible_phone: '',
};

export default function OrganizationSettings() {
  const [form, setForm] = useState(EMPTY_FORM);
  const [profile, setProfile] = useState(null);
  const [units, setUnits] = useState([]);
  const [unitForm, setUnitForm] = useState(EMPTY_UNIT);
  const [editingUnitId, setEditingUnitId] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [savingUnit, setSavingUnit] = useState(false);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const [res, unitsRes] = await Promise.all([
        getOrganizationProfile(),
        listOrganizationalUnits().catch(() => ({ units: [] })),
      ]);
      const p = res.profile || {};
      setProfile(p);
      setForm({
        employee_count: p.employee_count ?? '',
        address: p.address || '',
        document: formatCnpj(p.document || ''),
      });
      setUnits(unitsRes.units || []);
    } catch (err) {
      setError(err.message || 'Erro ao carregar cadastro organizacional.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  async function handleSave(e) {
    e.preventDefault();
    setSaving(true);
    setError('');
    setMessage('');
    try {
      const res = await updateOrganizationProfile({
        employee_count: form.employee_count === '' ? null : form.employee_count,
        address: form.address,
        document: form.document,
      });
      const p = res.profile || {};
      setProfile(p);
      setForm({
        employee_count: p.employee_count ?? '',
        address: p.address || '',
        document: formatCnpj(p.document || ''),
      });
      setMessage('Cadastro organizacional atualizado.');
    } catch (err) {
      setError(err.message || 'Erro ao salvar.');
    } finally {
      setSaving(false);
    }
  }

  async function handleSaveUnit(e) {
    e.preventDefault();
    setSavingUnit(true);
    setError('');
    setMessage('');
    try {
      const payload = {
        name: unitForm.name.trim(),
        unit_type: unitForm.unit_type,
        address: unitForm.address.trim() || null,
        responsible_name: unitForm.responsible_name.trim() || null,
        responsible_email: unitForm.responsible_email.trim() || null,
        responsible_phone: unitForm.responsible_phone.trim() || null,
      };
      if (!payload.name) {
        setError('Informe o nome da unidade organizacional.');
        return;
      }
      if (editingUnitId) {
        await updateOrganizationalUnit(editingUnitId, payload);
        setMessage('Unidade organizacional atualizada.');
      } else {
        await createOrganizationalUnit(payload);
        setMessage('Unidade organizacional criada.');
      }
      setUnitForm(EMPTY_UNIT);
      setEditingUnitId(null);
      await load();
    } catch (err) {
      setError(err.message || 'Erro ao salvar unidade organizacional.');
    } finally {
      setSavingUnit(false);
    }
  }

  async function handleDeactivateUnit(unit) {
    if (!window.confirm(`Desativar "${unit.name}"?`)) return;
    try {
      await deleteOrganizationalUnit(unit.id);
      setMessage(`${unit.name} desativada.`);
      if (editingUnitId === unit.id) {
        setEditingUnitId(null);
        setUnitForm(EMPTY_UNIT);
      }
      await load();
    } catch (err) {
      setError(err.message || 'Erro ao desativar.');
    }
  }

  const sitesByIndustry = profile?.sites_by_industry || {};
  const siteManagers = profile?.site_managers || [];
  const activeUnits = units.filter((u) => u.is_active !== false);

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <header>
        <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
          Organização
        </p>
        <h1 className="mt-1 text-2xl font-bold text-slate-900">Cadastro Organizacional</h1>
        <p className="mt-1 max-w-2xl text-sm text-slate-600">
          Dados cadastrais da empresa e unidades administrativas (filiais, escritórios,
          depósitos). Acesso ao sistema e papel funcional ficam em{' '}
          <Link to="/professionals-manager" className="font-semibold text-chameleon-dark underline">
            Meu Time
          </Link>
          .
        </p>
      </header>

      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
          {error}
        </div>
      )}
      {message && (
        <div className="rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-900">
          {message}
        </div>
      )}

      {loading ? (
        <p className="text-sm text-slate-500">Carregando…</p>
      ) : (
        <>
          <form
            onSubmit={handleSave}
            className="space-y-4 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm"
          >
            <h2 className="text-sm font-bold uppercase tracking-wide text-slate-700">
              Dados da empresa
            </h2>
            <label className="block text-xs font-semibold text-slate-600">
              Número de colaboradores
              <input
                type="number"
                min="0"
                value={form.employee_count}
                onChange={(e) => setForm((f) => ({ ...f, employee_count: e.target.value }))}
                className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                placeholder="Ex: 120"
              />
            </label>
            <label className="block text-xs font-semibold text-slate-600">
              Localização / Endereço
              <textarea
                value={form.address}
                onChange={(e) => setForm((f) => ({ ...f, address: e.target.value }))}
                rows={3}
                className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                placeholder="Cidade, estado, endereço da sede…"
              />
            </label>
            <label className="block text-xs font-semibold text-slate-600">
              CNPJ / Documento
              <input
                value={form.document}
                onChange={(e) =>
                  setForm((f) => ({ ...f, document: formatCnpj(e.target.value) }))
                }
                inputMode="numeric"
                autoComplete="off"
                maxLength={18}
                className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                placeholder="00.000.000/0000-00"
              />
            </label>
            <button
              type="submit"
              disabled={saving}
              className="rounded-lg bg-chameleon px-4 py-2 text-sm font-semibold text-white hover:bg-chameleon-dark disabled:opacity-50"
            >
              {saving ? 'Salvando…' : 'Salvar'}
            </button>
          </form>

          <section className="space-y-4 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
            <h2 className="text-sm font-bold uppercase tracking-wide text-slate-700">
              Unidades organizacionais
            </h2>
            <p className="text-xs text-slate-500">
              Filiais, escritórios e depósitos — contato cadastral do responsável (não é login).
            </p>

            <form onSubmit={handleSaveUnit} className="space-y-3 rounded-xl border border-slate-100 bg-slate-50/60 p-4">
              <h3 className="text-xs font-bold uppercase tracking-wide text-slate-600">
                {editingUnitId ? 'Editar unidade' : 'Nova unidade'}
              </h3>
              <div className="grid gap-3 sm:grid-cols-2">
                <label className="block text-xs font-semibold text-slate-600 sm:col-span-2">
                  Nome
                  <input
                    required
                    value={unitForm.name}
                    onChange={(e) => setUnitForm((f) => ({ ...f, name: e.target.value }))}
                    className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm"
                    placeholder="Ex: Filial Recife"
                  />
                </label>
                <label className="block text-xs font-semibold text-slate-600">
                  Tipo
                  <select
                    value={unitForm.unit_type}
                    onChange={(e) => setUnitForm((f) => ({ ...f, unit_type: e.target.value }))}
                    className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm"
                  >
                    {UNIT_TYPES.map((t) => (
                      <option key={t.value} value={t.value}>
                        {t.label}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="block text-xs font-semibold text-slate-600">
                  Telefone do responsável
                  <input
                    value={unitForm.responsible_phone}
                    onChange={(e) =>
                      setUnitForm((f) => ({ ...f, responsible_phone: e.target.value }))
                    }
                    className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm"
                    placeholder="(81) 99999-0000"
                  />
                </label>
                <label className="block text-xs font-semibold text-slate-600 sm:col-span-2">
                  Endereço
                  <input
                    value={unitForm.address}
                    onChange={(e) => setUnitForm((f) => ({ ...f, address: e.target.value }))}
                    className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm"
                    placeholder="Rua, bairro, cidade…"
                  />
                </label>
                <label className="block text-xs font-semibold text-slate-600">
                  Responsável (nome)
                  <input
                    value={unitForm.responsible_name}
                    onChange={(e) =>
                      setUnitForm((f) => ({ ...f, responsible_name: e.target.value }))
                    }
                    className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm"
                  />
                </label>
                <label className="block text-xs font-semibold text-slate-600">
                  E-mail do responsável
                  <input
                    type="email"
                    value={unitForm.responsible_email}
                    onChange={(e) =>
                      setUnitForm((f) => ({ ...f, responsible_email: e.target.value }))
                    }
                    className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm"
                  />
                </label>
              </div>
              <div className="flex gap-2">
                <button
                  type="submit"
                  disabled={savingUnit}
                  className="rounded-lg bg-chameleon px-4 py-2 text-sm font-semibold text-white hover:bg-chameleon-dark disabled:opacity-50"
                >
                  {savingUnit ? 'Salvando…' : editingUnitId ? 'Atualizar' : 'Adicionar'}
                </button>
                {editingUnitId && (
                  <button
                    type="button"
                    onClick={() => {
                      setEditingUnitId(null);
                      setUnitForm(EMPTY_UNIT);
                    }}
                    className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-700"
                  >
                    Cancelar
                  </button>
                )}
              </div>
            </form>

            <ul className="divide-y divide-slate-100 rounded-xl border border-slate-100">
              {activeUnits.length === 0 && (
                <li className="px-3 py-6 text-center text-sm text-slate-500">
                  Nenhuma unidade organizacional cadastrada.
                </li>
              )}
              {activeUnits.map((unit) => (
                <li
                  key={unit.id}
                  className="flex items-start justify-between gap-3 px-3 py-3 text-sm"
                >
                  <div>
                    <p className="font-semibold text-slate-900">
                      {unit.name}{' '}
                      <span className="text-xs font-medium text-slate-500">({unit.unit_type})</span>
                    </p>
                    {unit.address && (
                      <p className="text-xs text-slate-500">{unit.address}</p>
                    )}
                    <p className="mt-0.5 text-xs text-slate-500">
                      {unit.responsible_name || '— sem responsável —'}
                      {unit.responsible_email ? ` · ${unit.responsible_email}` : ''}
                      {unit.responsible_phone ? ` · ${unit.responsible_phone}` : ''}
                    </p>
                  </div>
                  <div className="flex shrink-0 flex-col items-end gap-1">
                    <button
                      type="button"
                      className="text-xs font-semibold text-chameleon-dark hover:underline"
                      onClick={() => {
                        setEditingUnitId(unit.id);
                        setUnitForm({
                          name: unit.name || '',
                          unit_type: unit.unit_type || 'Filial',
                          address: unit.address || '',
                          responsible_name: unit.responsible_name || '',
                          responsible_email: unit.responsible_email || '',
                          responsible_phone: unit.responsible_phone || '',
                        });
                      }}
                    >
                      Editar
                    </button>
                    <button
                      type="button"
                      className="text-xs font-semibold text-red-700 hover:underline"
                      onClick={() => handleDeactivateUnit(unit)}
                    >
                      Desativar
                    </button>
                  </div>
                </li>
              ))}
            </ul>
          </section>

          <section className="space-y-4 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <h2 className="text-sm font-bold uppercase tracking-wide text-slate-700">
                Unidades operacionais
              </h2>
              <Link
                to="/operational/sites"
                className="text-xs font-semibold text-chameleon-dark hover:underline"
              >
                Editar em Gestão de Unidades
              </Link>
            </div>
            <p className="text-sm text-slate-700">
              Operacionais: <strong>{profile?.sites_total ?? 0}</strong>
              {' · '}
              Organizacionais:{' '}
              <strong>{profile?.organizational_units_total ?? activeUnits.length}</strong>
            </p>
            {Object.keys(sitesByIndustry).length > 0 ? (
              <ul className="space-y-1 text-sm text-slate-600">
                {Object.entries(sitesByIndustry).map(([industry, count]) => (
                  <li key={industry}>
                    {getIndustryLabels(industry).unitPlural}: {count}
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-sm text-slate-500">Nenhuma unidade ativa cadastrada.</p>
            )}

            <h3 className="pt-2 text-xs font-bold uppercase tracking-wide text-slate-600">
              Gestores por unidade
            </h3>
            {siteManagers.length === 0 ? (
              <p className="text-sm text-slate-500">Sem unidades para exibir gestores.</p>
            ) : (
              <ul className="divide-y divide-slate-100 rounded-xl border border-slate-100">
                {siteManagers.map((row) => (
                  <li key={row.site_id} className="px-3 py-2 text-sm">
                    <p className="font-semibold text-slate-900">{row.site_name}</p>
                    <p className="text-xs text-slate-500">
                      {getIndustryLabels(row.industry_type).unit}
                      {row.organizational_unit_name
                        ? ` · ${row.organizational_unit_name}`
                        : ''}
                      {' · '}
                      {row.manager_name || '— não definido —'}
                    </p>
                  </li>
                ))}
              </ul>
            )}
          </section>
        </>
      )}
    </div>
  );
}
