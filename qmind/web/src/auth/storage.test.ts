import { describe, expect, it } from "vitest";
import {
  assertNoSensitiveLocalPersistence,
  clearAllLocalPersistence,
  readPreferredOrganizationId,
  writePreferredOrganizationId,
} from "@/auth/storage";

const ORG_A = "11111111-1111-4111-8111-111111111111";
const ORG_B = "22222222-2222-4222-8222-222222222222";

describe("local persistence policy", () => {
  it("stores only preferred organization UUID in sessionStorage", () => {
    writePreferredOrganizationId(ORG_A);
    expect(readPreferredOrganizationId()).toBe(ORG_A);
    writePreferredOrganizationId(ORG_B);
    expect(readPreferredOrganizationId()).toBe(ORG_B);
    assertNoSensitiveLocalPersistence();
  });

  it("rejects non-UUID preference", () => {
    writePreferredOrganizationId("not-a-uuid");
    expect(readPreferredOrganizationId()).toBeNull();
  });

  it("clears preference on logout path and has no token/tenant payloads", () => {
    writePreferredOrganizationId(ORG_A);
    localStorage.setItem("qmind.token", "eyJhbGciOiJIUzI1NiJ9.fake");
    clearAllLocalPersistence();
    expect(readPreferredOrganizationId()).toBeNull();
    expect(localStorage.getItem("qmind.token")).toBeNull();
    assertNoSensitiveLocalPersistence();
  });
});
