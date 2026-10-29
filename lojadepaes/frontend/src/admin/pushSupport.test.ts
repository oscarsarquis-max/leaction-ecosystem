import { describe, expect, it } from "vitest";
import { classifyPush } from "./pushSupport";

const ready = {
  configured: true,
  serviceWorker: true,
  pushManager: true,
  notification: true,
  permission: "default" as const,
  appleStandaloneProperty: false,
  standalone: false,
  serverActive: false,
};

describe("classifyPush", () => {
  it("keeps permission for the explicit click", () => {
    expect(classifyPush(ready)).toBe("available");
  });

  it("reports the states the administrator can act on", () => {
    expect(classifyPush({ ...ready, configured: false })).toBe("unconfigured");
    expect(classifyPush({ ...ready, permission: "denied" })).toBe("permission-blocked");
    expect(classifyPush({ ...ready, pushManager: false })).toBe("unsupported");
    expect(
      classifyPush({
        ...ready,
        pushManager: false,
        serviceWorker: false,
        notification: false,
        appleStandaloneProperty: true,
      }),
    ).toBe("needs-home-screen");
    expect(classifyPush({ ...ready, permission: "granted", serverActive: true })).toBe("active");
  });
});
