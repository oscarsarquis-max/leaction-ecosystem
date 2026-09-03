import { describe, it, expect, vi, afterEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { useExecutionPolling } from "./useExecutionPolling";

describe("useExecutionPolling", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("stops polling when the execution is terminal", async () => {
    const fetchMock = vi.fn(async () => ({
      ok: true,
      status: 200,
      text: async () => JSON.stringify({ summary: { executionId: "ex-1", state: "SUCCEEDED" } }),
    }));
    vi.stubGlobal("fetch", fetchMock);
    const { result } = renderHook(() =>
      useExecutionPolling("ex-1", { enabled: true, minIntervalMs: 40 }),
    );
    await waitFor(() => expect(result.current.status).toBe("terminal"));
    const calls = fetchMock.mock.calls.length;
    await new Promise((resolve) => setTimeout(resolve, 120));
    expect(fetchMock.mock.calls.length).toBe(calls);
  });

  it("does not start when disabled", async () => {
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
    renderHook(() => useExecutionPolling("ex-1", { enabled: false, minIntervalMs: 40 }));
    await new Promise((resolve) => setTimeout(resolve, 80));
    expect(fetchMock).not.toHaveBeenCalled();
  });
});
