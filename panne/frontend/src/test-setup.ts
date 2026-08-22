import "@testing-library/jest-dom/vitest";
import { expect } from "vitest";
import * as axeMatchers from "vitest-axe/matchers";

expect.extend(axeMatchers);

if (typeof crypto.randomUUID !== "function") {
  crypto.randomUUID = () => "00000000-0000-4000-8000-000000000000";
}

if (typeof crypto.randomUUID !== "function") {
  crypto.randomUUID = () => "00000000-0000-4000-8000-000000000000";
}
