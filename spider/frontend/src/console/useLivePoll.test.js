import { afterEach, describe, expect, it, vi } from "vitest";
import { act, renderHook, waitFor } from "@testing-library/react";
import { useLivePoll } from "./useLivePoll";

function deferred() {
  let resolve;
  let reject;
  const promise = new Promise((ok, fail) => {
    resolve = ok;
    reject = fail;
  });
  return { promise, resolve, reject };
}

afterEach(() => {
  vi.useRealTimers();
});

describe("useLivePoll", () => {
  it("recovers after a transient failure without dropping the last value", async () => {
    let n = 0;
    const run = vi.fn(async () => {
      n += 1;
      if (n === 2) throw new Error("offline");
      return n === 1 ? { items: ["keep"] } : { items: ["next"] };
    });
    const { result } = renderHook(() =>
      useLivePoll({
        enabled: true,
        intervalMs: 10_000,
        maxBackoffMs: 10_000,
        timeoutMs: 200,
        run,
        resetKey: "a",
        isTerminal: (value) => value.items?.[0] === "next",
      }),
    );
    await waitFor(() => expect(result.current.value).toEqual({ items: ["keep"] }));
    Object.defineProperty(document, "visibilityState", { configurable: true, get: () => "visible" });
    act(() => {
      document.dispatchEvent(new Event("visibilitychange"));
    });
    await waitFor(() => expect(result.current.stale).toBe(true));
    expect(result.current.value).toEqual({ items: ["keep"] });
    expect(result.current.status).toBe("error");
    act(() => {
      document.dispatchEvent(new Event("visibilitychange"));
    });
    await waitFor(() => expect(result.current.value).toEqual({ items: ["next"] }));
    expect(result.current.stale).toBe(false);
    expect(result.current.status).toBe("terminal");
  });

  it("does not surface an expected AbortError as a business failure", async () => {
    const abort = new Error("aborted");
    abort.name = "AbortError";
    const run = vi.fn().mockRejectedValue(abort);
    const { result } = renderHook(() =>
      useLivePoll({ enabled: true, intervalMs: 20, timeoutMs: 200, run, resetKey: "abort" }),
    );
    await waitFor(() => expect(run).toHaveBeenCalled());
    await new Promise((resolve) => setTimeout(resolve, 30));
    expect(result.current.error).toBe(null);
    expect(result.current.status).not.toBe("error");
  });

  it("resumes on visibility after a transient error", async () => {
    let n = 0;
    const run = vi.fn(async () => {
      n += 1;
      if (n === 1) throw new Error("blip");
      return { items: ["back"] };
    });
    const { result } = renderHook(() =>
      useLivePoll({ enabled: true, intervalMs: 10_000, maxBackoffMs: 10_000, timeoutMs: 200, run, resetKey: "vis" }),
    );
    await waitFor(() => expect(result.current.stale).toBe(true));
    Object.defineProperty(document, "visibilityState", { configurable: true, get: () => "visible" });
    act(() => {
      document.dispatchEvent(new Event("visibilitychange"));
    });
    await waitFor(() => expect(result.current.value).toEqual({ items: ["back"] }));
  });

  it("does not cancel a manual pause when the tab becomes visible", async () => {
    const run = vi.fn().mockResolvedValue({ items: ["one"] });
    const { result, rerender } = renderHook(
      ({ paused }) => useLivePoll({ enabled: true, paused, intervalMs: 20, timeoutMs: 200, run, resetKey: "p" }),
      { initialProps: { paused: false } },
    );
    await waitFor(() => expect(result.current.value).toEqual({ items: ["one"] }));
    const calls = run.mock.calls.length;
    rerender({ paused: true });
    await waitFor(() => expect(result.current.status).toBe("ok"));
    Object.defineProperty(document, "visibilityState", { configurable: true, get: () => "visible" });
    act(() => {
      document.dispatchEvent(new Event("visibilitychange"));
    });
    await new Promise((resolve) => setTimeout(resolve, 40));
    expect(run.mock.calls.length).toBe(calls);
  });

  it("ignores a delayed response after a newer request started", async () => {
    const first = deferred();
    const second = deferred();
    const run = vi.fn()
      .mockImplementationOnce(() => first.promise)
      .mockImplementationOnce(() => second.promise)
      .mockResolvedValue({ items: ["new"] });
    const { result, rerender } = renderHook(
      ({ forceKey }) =>
        useLivePoll({
          enabled: true,
          intervalMs: 10_000,
          timeoutMs: 500,
          run,
          resetKey: "late",
          forceKey,
          isTerminal: (value) => value.items?.[0] === "new",
        }),
      { initialProps: { forceKey: 0 } },
    );
    await waitFor(() => expect(run).toHaveBeenCalledTimes(1));
    rerender({ forceKey: 1 });
    await waitFor(() => expect(run).toHaveBeenCalledTimes(2));
    await act(async () => {
      second.resolve({ items: ["new"] });
      await second.promise;
    });
    await waitFor(() => expect(result.current.value).toEqual({ items: ["new"] }));
    await act(async () => {
      first.resolve({ items: ["old"] });
      await first.promise;
    });
    await new Promise((resolve) => setTimeout(resolve, 20));
    expect(result.current.value).toEqual({ items: ["new"] });
  });

  it("does not overlap in-flight requests", async () => {
    const pending = deferred();
    const run = vi.fn(() => pending.promise);
    renderHook(() => useLivePoll({ enabled: true, intervalMs: 10, timeoutMs: 500, run, resetKey: "one" }));
    await waitFor(() => expect(run).toHaveBeenCalledTimes(1));
    Object.defineProperty(document, "visibilityState", { configurable: true, get: () => "visible" });
    act(() => {
      document.dispatchEvent(new Event("visibilitychange"));
    });
    await new Promise((resolve) => setTimeout(resolve, 20));
    expect(run).toHaveBeenCalledTimes(1);
    await act(async () => {
      pending.resolve({ items: ["only"] });
      await pending.promise;
    });
  });

  it("stops on expired session and does not refresh again", async () => {
    const expired = new Error("Consulta da lista de execuções recusada (401).");
    expired.status = 401;
    const run = vi.fn().mockRejectedValue(expired);
    const { result } = renderHook(() =>
      useLivePoll({ enabled: true, intervalMs: 20, timeoutMs: 200, run, resetKey: "exp" }),
    );
    await waitFor(() => expect(result.current.auth).toBe("expired"));
    const calls = run.mock.calls.length;
    await new Promise((resolve) => setTimeout(resolve, 50));
    Object.defineProperty(document, "visibilityState", { configurable: true, get: () => "visible" });
    act(() => {
      document.dispatchEvent(new Event("visibilitychange"));
    });
    await new Promise((resolve) => setTimeout(resolve, 30));
    expect(run.mock.calls.length).toBe(calls);
    expect(result.current.status).toBe("expired");
  });

  it("clears cached value when access is denied", async () => {
    const denied = new Error("recusada (403)");
    denied.status = 403;
    let n = 0;
    const run = vi.fn(async () => {
      n += 1;
      if (n === 1) return { items: ["secret"] };
      throw denied;
    });
    const { result } = renderHook(() =>
      useLivePoll({ enabled: true, intervalMs: 10_000, maxBackoffMs: 10_000, timeoutMs: 200, run, resetKey: "den" }),
    );
    await waitFor(() => expect(result.current.value).toEqual({ items: ["secret"] }));
    Object.defineProperty(document, "visibilityState", { configurable: true, get: () => "visible" });
    act(() => {
      document.dispatchEvent(new Event("visibilitychange"));
    });
    await waitFor(() => expect(result.current.auth).toBe("denied"));
    expect(result.current.value).toBe(null);
  });

  it("does not poll a terminal result again until a manual force", async () => {
    const run = vi.fn().mockResolvedValue({ items: [{ eventType: "EXECUTION_SUCCEEDED" }] });
    const { rerender } = renderHook(
      ({ forceKey }) =>
        useLivePoll({
          enabled: true,
          intervalMs: 20,
          timeoutMs: 200,
          run,
          resetKey: "term",
          forceKey,
          isTerminal: (value) => value.items?.[0]?.eventType === "EXECUTION_SUCCEEDED",
        }),
      { initialProps: { forceKey: 0 } },
    );
    await waitFor(() => expect(run).toHaveBeenCalledTimes(1));
    await new Promise((resolve) => setTimeout(resolve, 40));
    expect(run).toHaveBeenCalledTimes(1);
    rerender({ forceKey: 2 });
    await waitFor(() => expect(run).toHaveBeenCalledTimes(2));
  });
});
