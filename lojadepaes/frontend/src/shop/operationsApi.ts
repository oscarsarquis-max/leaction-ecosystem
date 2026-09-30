import { requestJson } from "../services/http";

export type OperationsStatus = {
  preview_protection: boolean;
  orders_enabled: boolean;
  payments_enabled: boolean;
  date_requests_enabled: boolean;
  house_fidelity_active?: boolean;
  business_date?: string;
  message: string | null;
};

export function fetchOperations(): Promise<OperationsStatus> {
  return requestJson<OperationsStatus>("/api/v1/operations");
}
