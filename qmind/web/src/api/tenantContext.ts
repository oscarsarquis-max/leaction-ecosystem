/**
 * Imperative tenant context for the API client.
 * Updated synchronously on org switch so in-flight header wiring never lags React state.
 */

let activeOrganizationId: string | null = null;
let requestGeneration = 0;

export function setActiveOrganizationId(organizationId: string | null): void {
  activeOrganizationId = organizationId;
}

export function getActiveOrganizationId(): string | null {
  return activeOrganizationId;
}

export function bumpRequestGeneration(): number {
  requestGeneration += 1;
  return requestGeneration;
}

export function getRequestGeneration(): number {
  return requestGeneration;
}

export function resetTenantContext(): void {
  activeOrganizationId = null;
  requestGeneration = 0;
}
