import { describe, expect, it, beforeEach } from "vitest";
import {
  consumeReturnUrl,
  isSafeReturnUrl,
  readReturnUrl,
  writeReturnUrl,
} from "@/lib/returnUrl";

describe("returnUrl", () => {
  beforeEach(() => {
    sessionStorage.clear();
  });

  it("aceita apenas paths relativos seguros", () => {
    expect(isSafeReturnUrl("/assessments")).toBe(true);
    expect(isSafeReturnUrl("/guided-tour")).toBe(true);
    expect(isSafeReturnUrl("/assessments/abc/guided")).toBe(true);
    expect(isSafeReturnUrl("https://evil.com")).toBe(false);
    expect(isSafeReturnUrl("//evil.com")).toBe(false);
    expect(isSafeReturnUrl("/login")).toBe(false);
    expect(isSafeReturnUrl("/")).toBe(false);
    expect(isSafeReturnUrl("/auth/callback")).toBe(false);
  });

  it("persiste e consome uma única vez", () => {
    writeReturnUrl("/guided-tour");
    expect(readReturnUrl()).toBe("/guided-tour");
    expect(consumeReturnUrl("/assessments")).toBe("/guided-tour");
    expect(consumeReturnUrl("/assessments")).toBe("/assessments");
  });
});
