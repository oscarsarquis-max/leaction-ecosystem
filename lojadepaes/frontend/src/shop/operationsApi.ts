import { requestJson } from "../services/http";

export type OperationsStatus = {
  preview_protection: boolean;
  orders_enabled: boolean;
  payments_enabled: boolean;
  date_requests_enabled: boolean;
  message: string | null;
};

export function fetchOperations(): Promise<OperationsStatus> {
  return requestJson<OperationsStatus>("/api/v1/operations");
}
