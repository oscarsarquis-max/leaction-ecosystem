export type WeatherPeriod = 'SOL' | 'CHUVA' | 'NUBLADO';
export type CalendarStatus = 'empty' | 'draft' | 'finalized';
export type DailyLogStatus = 'Rascunho' | 'Assinado' | 'Sincronizado';

export interface ProjectSite {
  id: string;
  tenant_id: string;
  name: string;
  location?: string | null;
  rt_engineer_name?: string | null;
  created_at?: string;
}

export interface WorkforceRow {
  role: string;
  headcount: number;
  type?: 'Propria' | 'Terceirizada';
  presence_details?: string;
  absences_count: number;
  absences_details?: string;
  extra_hours_count: number;
  extra_hours_details?: string;
  general_remarks?: string;
}

export interface SupplyRow {
  key: string;
  label: string;
  quantity: number;
  unit: string;
  details?: string;
}

export interface EquipmentRow {
  key: string;
  label: string;
  equipment_name: string;
  status: string;
  quantity: number;
  remarks?: string;
}

export interface OccurrenceRow {
  type: string;
  exact_location: string;
  what_happened: string;
  immediate_action_taken?: string;
  safety_ppe_notes?: string;
}

export interface DailyLogPayload {
  project_id: string;
  date: string;
  weather_morning?: WeatherPeriod | null;
  weather_afternoon?: WeatherPeriod | null;
  technical_comments?: string;
  ppe_compliant?: boolean | null;
  ppe_compliant_details?: string;
  delay_waiting_material?: boolean;
  delay_rework?: boolean;
  delay_lack_of_front?: boolean;
  end_shift_clean?: boolean | null;
  end_shift_tools_stored?: boolean | null;
  end_shift_loose_materials?: boolean | null;
  sprint_daily_goal?: string;
  goal_achieved?: boolean | null;
  impediment_details?: string;
  mitigation_action?: string;
  preventive_action?: string;
  workforce?: WorkforceRow[];
  supplies?: SupplyRow[];
  equipment_statuses?: EquipmentRow[];
  occurrences?: OccurrenceRow[];
  finalize?: boolean;
  signed_by?: string;
}

export interface DailyLog extends DailyLogPayload {
  id: string;
  status: DailyLogStatus | string;
  is_signed: boolean;
  is_editable: boolean;
  calendar_status?: CalendarStatus;
  supplies?: SupplyRow[];
  equipment_statuses?: EquipmentRow[];
}

export interface CalendarDay {
  date: string;
  calendar_status: CalendarStatus;
  status: string | null;
  log_id: string | null;
  is_editable: boolean;
}

export interface MonthCalendar {
  year: number;
  month: number;
  project_id: string;
  days: CalendarDay[];
}
