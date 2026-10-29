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
  adaptation_attention?: boolean;
  has_custom?: boolean;
  custom_awaiting?: boolean;
  source?: "order" | "date_request";
  row_key?: string;
  desired_date?: string | null;
  context_label?: string | null;
  pending_hours?: number | null;
  overdue?: boolean;
  delivery_pending?: boolean;
  visible_stage?: string | null;
  visible_label?: string | null;
  payment_attention?: string | null;
};

export type OrderListResponse = {
  items: OrderListItem[];
  page: number;
  page_size: number;
  total: number;
  orders_error?: string | null;
  date_requests_error?: string | null;
  search_scope?: string | null;
  filter_label?: string | null;
  state_counts?: {
    queue: number;
    all: number;
    completed: number;
    cancelled: number;
    date_closed?: number;
  } | null;
};

export type DateRequestDetail = {
  id: string;
  public_reference: string;
  status: string;
  desired_date: string;
  proposed_date: string | null;
  customer_name: string;
  customer_email: string;
  intended_quantity: number | null;
  message: string | null;
  admin_note: string | null;
  cart_context: Array<{ product_name: string; variant_name: string; quantity: number }> | null;
  created_at: string;
  events: Array<{ action: string; actor_ref: string | null; detail: string | null; created_at: string }>;
  notifications: Array<{ id?: string | null; kind: string; status: string; last_error?: string | null }>;
  allowed_actions: string[];
  reply_preview: string | null;
  converted_order_id?: string | null;
  converted_order_href?: string | null;
  accept_preview?: AcceptPreview | null;
};

export type CatalogChoice = {
  product_id: string;
  variant_id: string;
  product_name: string;
  variant_name: string;
  unit_cents: number;
};

export type AcceptPreview = {
  can_accept: boolean;
  gaps: string[];
  desired_date: string;
  accepted_date: string;
  items: Array<{
    product_name: string;
    variant_name: string;
    quantity: number;
    unit_cents: number;
    line_cents: number;
    variant_id?: string;
  }>;
  total_cents: number | null;
  currency: string;
  has_address: boolean;
  delivery_pending?: boolean;
  converted_order_id: string | null;
  awaiting_details: boolean;
  needs_catalog_choice?: boolean;
  informed_quantity?: number | null;
  ask_customer?: boolean;
  suggestion?: {
    product_name: string;
    variant_name: string | null;
    variant_id: string | null;
    unit_cents: number | null;
    reason: string;
  } | null;
  catalog_choices?: CatalogChoice[];
  complementary_pending?: string[];
};

export type BoardMetric = {
  label: string;
  count: number;
  lens: string;
};

export type AttendanceBoard = {
  scope: string;
  timezone: string;
  updated_label: string;
  operational_total: number;
  stages: BoardMetric[];
  exceptions?: BoardMetric[];
  composition_note?: string;
  history: BoardMetric[];
  payment_note: string;
  payments: BoardMetric[];
  payment_other: BoardMetric[];
  payment_orders: number;
  payment_scope_label?: string;
  work_payments?: BoardMetric[];
  work_payment_orders?: number;
  excluded_tests?: number;
  excluded_holding_capacity?: number;
  pending_note: string;
  pendings: BoardMetric[];
  not_tracked: Array<{ label: string; reason: string }>;
  legacy_note?: string;
};

export type AttendanceSummary = {
  date_requests_awaiting: number;
  orders_awaiting_evaluation: number;
  orders_awaiting_adaptation: number;
  paid_awaiting_accept: number;
  confirmed_awaiting_delivery: number;
  overdue_dates: number;
  unique_records: number;
  counts_are_subsets: boolean;
  priority: Array<{
    source: string;
    id: string;
    row_key: string;
    public_reference: string;
    kind_label: string;
    action_label: string;
    href: string;
    desired_date: string | null;
    overdue: boolean;
  }>;
  updated_at: string;
  board?: AttendanceBoard;
  owner_alerts?: {
    email: { active: boolean; destination_configured: boolean; delivery_confirmed: boolean };
    whatsapp: {
      active: boolean;
      destination_configured: boolean;
      delivery_confirmed: boolean;
      block: string | null;
    };
    failures: Array<{ id: string; channel: string; kind: string; status: string; last_error: string | null }>;
  };
  dispatch?: { id: string; status: string; last_error: string | null } | null;
};

export type Extra = {
  ingredient_id: string;
  name: string;
  surcharge: Money | null;
  included_in_loaf_price?: boolean;
  snapshot_complete: boolean;
  assistant_role?: string | null;
};

export type ItemAdaptation = {
  id: string;
  status: string;
  customer_text: string;
  reason: string | null;
  bakery_response: string;
  client_decision: string | null;
  applies_to_all_units_of_this_line: boolean;
  resolved: boolean;
  history: Array<{
    id: string;
    from_status: string | null;
    to_status: string;
    actor_kind: string;
    created_at: string;
    has_note: boolean;
  }>;
};

export type OrderItem = {
  id: string;
  dough_name: string;
  shape_name: string;
  quantity: number;
  unit_price: Money;
  line_total: Money;
  extras: Extra[];
  origin?: string;
  weight_grams?: number | null;
  snapshot_complete: boolean;
  provisional: boolean;
  adaptation?: ItemAdaptation | null;
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
  sanitized_error: string | null;
  method: string | null;
  pix_expires_at: string | null;
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
  fulfilled_at?: string | null;
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
  production_local_date: string | null;
  preferred_time: string | null;
  proposed_production_date: string | null;
  has_unresolved_adaptations?: boolean;
  fidelity_opt_in?: boolean;
  order_kind?: string;
  fidelity_cpf_masked?: string | null;
  has_custom?: boolean;
  notifications?: Array<{
    id?: string | null;
    kind: string;
    status: string;
    last_error?: string | null;
    sent_at?: string | null;
  }>;
  delivery_pending?: boolean;
  delivery_missing_fields?: string[];
  linked_delivery_filled_fields?: string[];
  visible_stage?: string | null;
  visible_label?: string | null;
  payment_attention?: string | null;
  delivery_confirmed_at?: string | null;
};

export type UnpaidProductionPrompt = {
  public_reference: string;
  total_cents: number | null;
  currency: string;
  financial_label: string;
  uncertain: boolean;
};

export type OrderFilters = {
  reference: string;
  status: string;
  created_from: string;
  created_to: string;
  modality: string;
  lens?: string;
};
