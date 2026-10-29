import { adminRequest } from "./api";

const DEVICE_KEY = "lojadepaes_push_device";

export function storedPushDevice(): string | null {
  return localStorage.getItem(DEVICE_KEY);
}

export function rememberPushDevice(id: string): void {
  localStorage.setItem(DEVICE_KEY, id);
}

export function forgetPushDevice(): void {
  localStorage.removeItem(DEVICE_KEY);
}

export async function deactivateStoredPush(): Promise<void> {
  const id = storedPushDevice();
  if (!id) {
    return;
  }
  try {
    await adminRequest(`/api/v1/admin/ops/push/devices/${id}/revoke`, { method: "POST" });
  } catch {
    // O logout explícito segue mesmo se o aparelho já estiver inativo.
  }
  forgetPushDevice();
}
