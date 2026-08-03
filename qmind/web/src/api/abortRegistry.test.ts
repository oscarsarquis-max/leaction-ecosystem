import { describe, expect, it } from "vitest";
import {
  abortAllInFlight,
  createTrackedAbortController,
} from "@/api/abortRegistry";

describe("abortRegistry", () => {
  it("aborts all tracked in-flight controllers", () => {
    const a = createTrackedAbortController();
    const b = createTrackedAbortController();
    expect(a.signal.aborted).toBe(false);
    abortAllInFlight("tenant_switch");
    expect(a.signal.aborted).toBe(true);
    expect(b.signal.aborted).toBe(true);
  });
});
