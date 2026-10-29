export type PushAvailability =
  | "unconfigured"
  | "unsupported"
  | "needs-home-screen"
  | "permission-blocked"
  | "available"
  | "active";

export function classifyPush(input: {
  configured: boolean;
  serviceWorker: boolean;
  pushManager: boolean;
  notification: boolean;
  permission: NotificationPermission | "unsupported";
  appleStandaloneProperty: boolean;
  standalone: boolean;
  serverActive: boolean;
}): PushAvailability {
  if (!input.configured) {
    return "unconfigured";
  }
  if (input.permission === "denied") {
    return "permission-blocked";
  }
  const supported = input.serviceWorker && input.pushManager && input.notification;
  if (!supported) {
    if (input.appleStandaloneProperty && !input.standalone) {
      return "needs-home-screen";
    }
    return "unsupported";
  }
  if (input.serverActive && input.permission === "granted") {
    return "active";
  }
  return "available";
}
