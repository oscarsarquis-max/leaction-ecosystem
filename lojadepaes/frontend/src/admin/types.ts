export type Money = {
  cents: number | null;
  currency: string;
};

export type FinancialKind = "none" | "unknown" | "open" | "settled";

export type SessionInfo = {
  username: string;
  csrf_token: string;
  bakery_timezone: string;
};

export type OrderListItem = {
  id: string;
  public_reference: string;
  created_at: string;
  status: string;
  customer_name: string | null;
  bread_units: number;
  fulfillment_modality: string | null;
  production_batch_id: string | null;
  production_batch_code: string | null;
  fulfillment_slot_id: string | null;
  slot_starts_at: string | null;
  slot_ends_at: string | null;
  total: Money;
  financial_kind: FinancialKind;
};

export type OrderListResponse = {
  items: OrderListItem[];
  page: number;
  page_size: number;
  total: number;
};

export type Extra = {
  ingredient_id: string;
  name: string;
  surcharge: Money;
  snapshot_complete: boolean;
};

export type OrderItem = {
  id: string;
  dough_name: string;
  shape_name: string;
  quantity: number;
  unit_price: Money;
  line_total: Money;
  extras: Extra[];
  snapshot_complete: boolean;
  provisional: boolean;
};

export type HistoryEntry = {
  id: string;
  from_status: string | null;
  to_status: string;
  reason: string | null;
  actor_ref: string | null;
  created_at: string;
};

export type Note = {
  id: string;
  body: string;
  author_ref: string | null;
  created_at: string;
};

export type PaymentRecord = {
  id: string;
  provider: string;
  external_reference: string | null;
  expected_cents: number;
  currency: string;
  financial_status: string;
  external_status_raw: string | null;
  amount_paid_cents: number | null;
  amount_refunded_cents: number | null;
  confirmed_at: string | null;
  last_synced_at: string | null;
};

export type PaymentEvent = {
  id: string;
  external_event_id: string;
  payment_record_id: string | null;
  external_type: string | null;
  received_at: string;
  provider_occurred_at: string | null;
  process_status: string;
  sanitized_error: string | null;
};

export type OrderDetail = {
  id: string;
  public_reference: string;
  created_at: string;
  updated_at: string;
  status: string;
  allowed_actions: string[];
  customer_name: string | null;
  customer_email: string | null;
  customer_phone: string | null;
  address: {
    street: string | null;
    number: string | null;
    complement: string | null;
    district: string | null;
    city: string | null;
    state: string | null;
    postal_code: string | null;
  };
  customer_note: string;
  fulfillment_modality: string | null;
  production_batch_code: string | null;
  slot_starts_at: string | null;
  slot_ends_at: string | null;
  confirmed_at: string | null;
  production_started_at: string | null;
  ready_at: string | null;
  completed_at: string | null;
  cancelled_at: string | null;
  cancellation_reason: string | null;
  currency: string;
  subtotal: Money;
  delivery_fee: Money;
  discount: Money;
  total: Money;
  items: OrderItem[];
  history: HistoryEntry[];
  notes: Note[];
  payment_records: PaymentRecord[];
  payment_events: PaymentEvent[];
  financial_kind: FinancialKind;
  financially_settled: boolean;
  holds_capacity: boolean;
  snapshots_locked: boolean;
};

export type OrderFilters = {
  reference: string;
  status: string;
  created_from: string;
  created_to: string;
  modality: string;
};
