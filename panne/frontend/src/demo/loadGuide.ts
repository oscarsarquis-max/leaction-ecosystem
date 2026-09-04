import { config } from "../config";
import { DEMO_GUIDE_FALLBACK } from "./guideFallback";
import type { DemoGuidePayload } from "./guideTypes";

export async function loadDemoGuide(): Promise<DemoGuidePayload> {
  if (!config.demoMode) {
    return DEMO_GUIDE_FALLBACK;
  }
  const base = config.apiBase.replace(/\/$/, "");
  try {
    const res = await fetch(`${base}/api/v1/public/demo-guide`, {
      method: "GET",
      headers: { Accept: "application/json" },
    });
    if (!res.ok) return { ...DEMO_GUIDE_FALLBACK, source: "fallback" };
    const data = (await res.json()) as DemoGuidePayload;
    if (!data || typeof data !== "object" || !Array.isArray(data.profiles)) {
      return { ...DEMO_GUIDE_FALLBACK, source: "fallback" };
    }
    return data;
  } catch {
    return { ...DEMO_GUIDE_FALLBACK, source: "fallback" };
  }
}
