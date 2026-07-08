import { useState, type FormEvent } from 'react';
import { createSite } from '../api/rdoApi';
import type { ProjectSite } from '../types';

interface Props {
  open: boolean;
  tenantId: string;
  onClose: () => void;
  onCreated: (site: ProjectSite) => void;
}

export default function NewSiteModal({ open, tenantId, onClose, onCreated }: Props) {
  const [name, setName] = useState('');
  const [location, setLocation] = useState('');
  const [rtEngineer, setRtEngineer] = useState('');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  if (!open) return null;

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setSaving(true);
    setError('');
    try {
      const site = await createSite({
        tenant_id: tenantId,
        name: name.trim(),
        location: location.trim() || undefined,
        rt_engineer_name: rtEngineer.trim() || undefined,
      });
      onCreated(site);
      setName('');
      setLocation('');
      setRtEngineer('');
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erro ao criar canteiro.');
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/50 p-4 sm:items-center">
      <div className="w-full max-w-md rounded-2xl bg-white p-5 shadow-2xl">
        <h2 className="text-lg font-bold text-slate-900">Novo Canteiro</h2>
        <p className="mt-1 text-sm text-slate-500">Cadastro rápido para iniciar o RDO do dia.</p>

        <form onSubmit={handleSubmit} className="mt-4 space-y-3">
          <label className="block">
            <span className="text-sm font-medium text-slate-700">Nome do canteiro *</span>
            <input
              required
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="mt-1 w-full rounded-xl border border-slate-200 px-3 py-3 text-base outline-none ring-emerald-500 focus:ring-2"
              placeholder="Ex: Residencial Parque Verde"
            />
          </label>
          <label className="block">
            <span className="text-sm font-medium text-slate-700">Localização</span>
            <input
              value={location}
              onChange={(e) => setLocation(e.target.value)}
              className="mt-1 w-full rounded-xl border border-slate-200 px-3 py-3 text-base outline-none ring-emerald-500 focus:ring-2"
              placeholder="Cidade / endereço"
            />
          </label>
          <label className="block">
            <span className="text-sm font-medium text-slate-700">Eng. responsável (RT)</span>
            <input
              value={rtEngineer}
              onChange={(e) => setRtEngineer(e.target.value)}
              className="mt-1 w-full rounded-xl border border-slate-200 px-3 py-3 text-base outline-none ring-emerald-500 focus:ring-2"
              placeholder="Nome do RT"
            />
          </label>

          {error && (
            <p className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>
          )}

          <div className="flex gap-2 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="min-h-12 flex-1 rounded-xl border border-slate-200 font-semibold text-slate-700"
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={saving}
              className="min-h-12 flex-1 rounded-xl bg-emerald-600 font-bold text-white disabled:opacity-60"
            >
              {saving ? 'Salvando…' : 'Criar'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
