import { useEffect, useState } from "react";
import { adminRequest } from "./api";
import { forgetPushDevice, rememberPushDevice, storedPushDevice } from "./pushClient";
import { classifyPush, type PushAvailability } from "./pushSupport";

type Device = { id: string; label: string; active: boolean; created_at: string };
type PushConfig = { configured: boolean; public_key: string; receipt_confirmed: boolean };

function permissionOf(): NotificationPermission | "unsupported" {
  return "Notification" in window ? Notification.permission : "unsupported";
}

function standaloneNow(): boolean {
  return (
    window.matchMedia("(display-mode: standalone)").matches ||
    ("standalone" in navigator && Boolean((navigator as Navigator & { standalone?: boolean }).standalone))
  );
}

function urlBase64ToBytes(value: string): ArrayBuffer {
  const padded = value + "=".repeat((4 - (value.length % 4)) % 4);
  const raw = atob(padded.replace(/-/g, "+").replace(/_/g, "/"));
  const buffer = new ArrayBuffer(raw.length);
  const view = new Uint8Array(buffer);
  for (let index = 0; index < raw.length; index += 1) {
    view[index] = raw.charCodeAt(index);
  }
  return buffer;
}

export function PushNotices() {
  const [availability, setAvailability] = useState<PushAvailability>("unconfigured");
  const [devices, setDevices] = useState<Device[]>([]);
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);
  const [publicKey, setPublicKey] = useState("");

  async function refresh() {
    const config = await adminRequest<PushConfig>("/api/v1/admin/ops/push");
    const listed = await adminRequest<{ devices: Device[] }>("/api/v1/admin/ops/push/devices");
    setPublicKey(config.public_key);
    setDevices(listed.devices);
    const current = storedPushDevice();
    const serverActive = listed.devices.some((device) => device.id === current && device.active);
    setAvailability(
      classifyPush({
        configured: config.configured,
        serviceWorker: "serviceWorker" in navigator,
        pushManager: "PushManager" in window,
        notification: "Notification" in window,
        permission: permissionOf(),
        appleStandaloneProperty: "standalone" in navigator,
        standalone: standaloneNow(),
        serverActive,
      }),
    );
  }

  useEffect(() => {
    void refresh().catch(() => setNote("Não foi possível ler o estado das notificações."));
  }, []);

  async function activate() {
    if (!publicKey || !("Notification" in window) || !("serviceWorker" in navigator)) {
      return;
    }
    setBusy(true);
    setNote("");
    try {
      const permission = await Notification.requestPermission();
      if (permission !== "granted") {
        setAvailability("permission-blocked");
        setNote("A permissão não foi concedida. O pedido não se repete sozinho.");
        return;
      }
      const registration = await navigator.serviceWorker.register("/sw.js");
      const subscription = await registration.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: urlBase64ToBytes(publicKey),
      });
      const json = subscription.toJSON();
      const saved = await adminRequest<{ id: string }>("/api/v1/admin/ops/push/subscriptions", {
        method: "POST",
        body: JSON.stringify({
          endpoint: subscription.endpoint,
          p256dh: json.keys?.p256dh,
          auth: json.keys?.auth,
          label: "Este aparelho",
        }),
      });
      rememberPushDevice(saved.id);
      setNote("Ativo neste aparelho. Isso ainda não prova que um aviso chegou ao celular.");
      await refresh();
    } catch {
      setNote("Não foi possível ativar neste aparelho.");
    } finally {
      setBusy(false);
    }
  }

  async function deactivate() {
    const id = storedPushDevice();
    setBusy(true);
    try {
      const registration = await navigator.serviceWorker?.getRegistration();
      const subscription = await registration?.pushManager.getSubscription();
      await subscription?.unsubscribe();
      if (id) {
        await adminRequest(`/api/v1/admin/ops/push/devices/${id}/revoke`, { method: "POST" });
      }
      forgetPushDevice();
      setNote("Este aparelho foi desativado.");
      await refresh();
    } catch {
      setNote("Não foi possível desativar este aparelho.");
    } finally {
      setBusy(false);
    }
  }

  async function sendTest() {
    const id = storedPushDevice();
    if (!id) {
      return;
    }
    setBusy(true);
    try {
      const result = await adminRequest<{ status: string; receipt_confirmed: boolean }>(
        `/api/v1/admin/ops/push/devices/${id}/test`,
        { method: "POST" },
      );
      setNote(
        result.status === "accepted"
          ? "O serviço aceitou o teste. Isso não confirma que ele apareceu no celular."
          : "O teste não foi aceito pelo serviço. Nenhum e-mail foi enviado.",
      );
    } catch {
      setNote("O teste não foi enviado.");
    } finally {
      setBusy(false);
    }
  }

  async function revoke(id: string) {
    setBusy(true);
    try {
      await adminRequest(`/api/v1/admin/ops/push/devices/${id}/revoke`, { method: "POST" });
      if (storedPushDevice() === id) {
        forgetPushDevice();
      }
      await refresh();
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="admin-push" aria-labelledby="admin-push-title">
      <h2 id="admin-push-title">Notificações neste aparelho</h2>
      <p>{copyFor(availability)}</p>
      {availability === "available" ? (
        <button type="button" className="admin-primary" disabled={busy} onClick={() => void activate()}>
          Ativar notificações neste aparelho
        </button>
      ) : null}
      {availability === "active" ? (
        <div className="admin-actions">
          <button type="button" className="admin-secondary" disabled={busy} onClick={() => void deactivate()}>
            Desativar neste aparelho
          </button>
          <button type="button" className="admin-secondary" disabled={busy} onClick={() => void sendTest()}>
            Enviar notificação de teste neste aparelho
          </button>
        </div>
      ) : null}
      {note ? <p className="admin-muted">{note}</p> : null}
      <details>
        <summary>Como ativar no Android e no iPhone</summary>
        <p>
          No Android compatível, toque em Ativar e permita o aviso. Se a permissão estiver bloqueada, libere as
          notificações da Loja nas configurações do site. O sistema, a conexão e as configurações do aparelho podem
          impedir a entrega.
        </p>
        <p>
          No iPhone ou iPad compatível, use o Safari, toque em Compartilhar e adicione a Loja à Tela de Início. Abra
          pelo ícone, entre na área administrativa e só então toque em Ativar. O Safari aberto como página comum não
          recebe este aviso.
        </p>
      </details>
      {devices.length > 0 ? (
        <ul className="admin-push-devices">
          {devices.map((device) => (
            <li key={device.id}>
              <span>
                {device.label} · {device.active ? "ativo" : "inativo"}
              </span>
              {device.active ? (
                <button type="button" className="admin-link" disabled={busy} onClick={() => void revoke(device.id)}>
                  Revogar
                </button>
              ) : null}
            </li>
          ))}
        </ul>
      ) : null}
    </section>
  );
}

function copyFor(availability: PushAvailability): string {
  if (availability === "unconfigured") {
    return "Configuração indisponível neste servidor. Nenhuma notificação será enviada.";
  }
  if (availability === "unsupported") {
    return "Este navegador não oferece notificação da Loja.";
  }
  if (availability === "needs-home-screen") {
    return "Adicione a Loja à Tela de Início, abra pelo ícone e então ative as notificações.";
  }
  if (availability === "permission-blocked") {
    return "A permissão está bloqueada neste navegador. Libere as notificações da Loja nas configurações do site.";
  }
  if (availability === "active") {
    return "Ativo neste aparelho.";
  }
  return "Disponível para ativar. A permissão só é pedida depois do clique.";
}
