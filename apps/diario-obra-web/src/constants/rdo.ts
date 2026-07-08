import type { EquipmentRow, SupplyRow, WorkforceRow } from '../types';

export const DEFAULT_WORKFORCE: WorkforceRow[] = [
  {
    role: 'Pedreiro',
    headcount: 0,
    type: 'Propria',
    absences_count: 0,
    extra_hours_count: 0,
  },
  {
    role: 'Servente',
    headcount: 0,
    type: 'Propria',
    absences_count: 0,
    extra_hours_count: 0,
  },
  {
    role: 'Eletricista',
    headcount: 0,
    type: 'Propria',
    absences_count: 0,
    extra_hours_count: 0,
  },
  {
    role: 'Carpinteiro',
    headcount: 0,
    type: 'Propria',
    absences_count: 0,
    extra_hours_count: 0,
  },
  {
    role: 'Armador',
    headcount: 0,
    type: 'Propria',
    absences_count: 0,
    extra_hours_count: 0,
  },
];

export const DEFAULT_SUPPLIES: SupplyRow[] = [
  { key: 'cement_bags', label: 'Sacos de cimento', quantity: 0, unit: 'sc' },
  { key: 'sand_m3', label: 'Areia', quantity: 0, unit: 'm³' },
  { key: 'gravel_m3', label: 'Brita', quantity: 0, unit: 'm³' },
  { key: 'steel_kg', label: 'Aço', quantity: 0, unit: 'kg' },
];

export const DEFAULT_EQUIPMENT: EquipmentRow[] = [
  {
    key: 'guindaste',
    label: 'Guindaste',
    equipment_name: 'Guindaste',
    status: 'Parado por Quebra',
    quantity: 0,
  },
  {
    key: 'betoneira',
    label: 'Betoneira',
    equipment_name: 'Betoneira',
    status: 'Parado por Quebra',
    quantity: 0,
  },
  {
    key: 'escavadeira',
    label: 'Escavadeira',
    equipment_name: 'Escavadeira',
    status: 'Parado por Quebra',
    quantity: 0,
  },
  {
    key: 'guindaste_operando',
    label: 'Guindaste operando',
    equipment_name: 'Guindaste',
    status: 'Operando',
    quantity: 0,
  },
];

export const TABS = ['Clima', 'Efetivo', 'Segurança', 'Ocorrências', 'Insumos', 'Daily Ágil'] as const;
export type TabId = (typeof TABS)[number];

export const OCCURRENCE_TYPES = [
  { value: 'Acidente', label: 'Machucou alguém' },
  { value: 'Falta_Material', label: 'Faltou material' },
  { value: 'Queda_Energia', label: 'Caiu a energia' },
  { value: 'Chuva_Forte', label: 'Chuva forte' },
  { value: 'Geral', label: 'Outro problema' },
] as const;
