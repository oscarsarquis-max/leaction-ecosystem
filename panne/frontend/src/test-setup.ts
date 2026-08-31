import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterEach, expect } from "vitest";
import * as axeMatchers from "vitest-axe/matchers";

afterEach(() => {
  cleanup();
});

expect.extend(axeMatchers);

if (typeof crypto.randomUUID !== "function") {
  crypto.randomUUID = () => "00000000-0000-4000-8000-000000000000";
}

/** jsdom não implementa matchMedia — usado pelo coach recolhível (≤720px). */
if (typeof window.matchMedia !== "function") {
  window.matchMedia = ((query: string) =>
    ({
      matches: false,
      media: query,
      onchange: null,
      addListener: () => undefined,
      removeListener: () => undefined,
      addEventListener: () => undefined,
      removeEventListener: () => undefined,
      dispatchEvent: () => false,
    }) as MediaQueryList);
}
