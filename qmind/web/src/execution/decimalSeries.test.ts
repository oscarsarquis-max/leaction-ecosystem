import { describe, expect, it } from "vitest";
import { seriesPositions } from "@/execution/decimalSeries";

describe("seriesPositions", () => {
  it("places the smallest at the bottom and the largest at the top", () => {
    expect(seriesPositions(["10.00", "20.00", "30.00"])).toEqual([0, 0.5, 1]);
  });

  it("keeps a flat series in the middle instead of dividing by zero", () => {
    expect(seriesPositions(["7.50", "7.50"])).toEqual([0.5, 0.5]);
  });

  it("compares values with different numbers of decimals", () => {
    expect(seriesPositions(["1", "1.5", "2.000"])).toEqual([0, 0.5, 1]);
  });

  it("handles negative values", () => {
    expect(seriesPositions(["-10", "0", "10"])).toEqual([0, 0.5, 1]);
  });

  it("separates decimals that a float would collapse into one point", () => {
    // As numbers, 0.1 + 0.2 and 0.3 are indistinguishable; as decimals they are
    // three different readings and the middle one must not sit at an extreme.
    const positions = seriesPositions([
      "0.30000000000000000000",
      "0.30000000000000000001",
      "0.30000000000000000002",
    ]);
    expect(positions).toEqual([0, 0.5, 1]);
  });

  it("does not overflow on values far beyond what a float can hold", () => {
    const positions = seriesPositions([
      "100000000000000000000000000000",
      "200000000000000000000000000000",
      "300000000000000000000000000000",
    ]);
    expect(positions).toEqual([0, 0.5, 1]);
    expect(positions?.every((p) => Number.isFinite(p))).toBe(true);
  });

  it("refuses a series it cannot read exactly, so no wrong line is drawn", () => {
    expect(seriesPositions(["12.00", "não medido"])).toBeNull();
    expect(seriesPositions(["1e40", "2"])).toBeNull();
    expect(seriesPositions([])).toBeNull();
  });
});
