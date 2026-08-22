import { assertAuthProviderAllowed, config } from "../config";
import { FakeAuthProvider } from "./FakeAuthProvider";
import { OidcAuthProvider } from "./OidcAuthProvider";
import type { AuthProvider } from "./types";

export function createAuthProvider(): AuthProvider {
  assertAuthProviderAllowed();
  if (config.authProvider === "oidc") return new OidcAuthProvider();
  return new FakeAuthProvider();
}
