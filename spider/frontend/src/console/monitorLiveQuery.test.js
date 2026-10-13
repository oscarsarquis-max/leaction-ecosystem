import { describe, expect, it } from "vitest";
import {
  classifyLiveFailure,
  isExpectedAbort,
  liveStreamLabel,
  liveStreamTone,
  monitorSelectionWanted,
  nextLiveBackoff,
  replaceMonitorSelectionSearch,
  safeMonitorReturnTo,
  shouldHoldManualMonitorSelection,
  shouldResumeOnVisible,
} from "./monitorLiveQuery";

describe("monitorLiveQuery", () => {
  it("does not treat an expected abort as a business failure", () => {
    const signal = { aborted: true };
    expect(isExpectedAbort({ name: "AbortError" }, signal)).toBe(true);
    expect(classifyLiveFailure({ name: "AbortError" })).toBe("abort");
  });

  it("classifies session, denial and transport separately", () => {
    expect(classifyLiveFailure({ status: 401 })).toBe("expired");
    expect(classifyLiveFailure({ status: 403 })).toBe("denied");
    expect(classifyLiveFailure({ status: 404 })).toBe("missing");
    expect(classifyLiveFailure(new Error("offline"))).toBe("transient");
  });

  it("caps backoff", () => {
    expect(nextLiveBackoff(1, 4000, 15000)).toBe(8000);
    expect(nextLiveBackoff(8, 4000, 15000)).toBe(15000);
  });

  it("does not announce live when stale or paused", () => {
    expect(liveStreamLabel({ paused: true })).toBe("Pausado");
    expect(liveStreamLabel({ stale: true, updatedAt: "2026-10-02T12:00:00Z", formatWhen: () => "12:00" })).toBe(
      "Desatualizado · última atualização 12:00",
    );
    expect(liveStreamTone({ stale: true })).toBe("stale");
    expect(liveStreamTone({ paused: false, stale: false })).toBe("live");
  });

  it("does not resume when paused, expired, denied or terminal", () => {
    expect(shouldResumeOnVisible({ paused: true, auth: null, terminal: false })).toBe(false);
    expect(shouldResumeOnVisible({ paused: false, auth: "expired", terminal: false })).toBe(false);
    expect(shouldResumeOnVisible({ paused: false, auth: "denied", terminal: false })).toBe(false);
    expect(shouldResumeOnVisible({ paused: false, auth: null, terminal: true })).toBe(false);
    expect(shouldResumeOnVisible({ paused: false, auth: null, terminal: false })).toBe(true);
  });

  it("does not let a Finance deep link override a later manual selection", () => {
    const finance = "afm-d3288e80-77cb-41d6-8c6d-8e0214ad25c3";
    expect(monitorSelectionWanted(`?q=${finance}&execution=${finance}`)).toBe(finance);
    expect(shouldHoldManualMonitorSelection(true, finance, "exec-retry-1")).toBe(true);
    expect(shouldHoldManualMonitorSelection(false, finance, finance)).toBe(false);
    expect(replaceMonitorSelectionSearch(`?q=${finance}&execution=${finance}`, "exec-retry-1")).toBe(
      "?execution=exec-retry-1",
    );
  });

  it("keeps a safe Monitor destination without token query params", () => {
    expect(safeMonitorReturnTo({ pathname: "/console", search: "?execution=sat-1" })).toBe(
      "/console?execution=sat-1",
    );
    expect(safeMonitorReturnTo({ pathname: "/console", search: "?code=abc" })).toBe("/console");
    expect(safeMonitorReturnTo({ pathname: "//evil", search: "" })).toBe("/");
  });
});
