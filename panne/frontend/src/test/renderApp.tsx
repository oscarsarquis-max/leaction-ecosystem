import { render, type RenderResult } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { AppRoutes } from "../App";
import { FakeAuthProvider } from "../auth/FakeAuthProvider";
import { AuthProviderTree } from "../auth/AuthContext";
import { AssistantProvider } from "../assistant/AssistantContext";
import { OrganizationProvider } from "../session/OrganizationContext";

export async function renderApp(
  path: string,
  options: { signedIn?: boolean } = {},
): Promise<{ provider: FakeAuthProvider; view: RenderResult }> {
  const provider = new FakeAuthProvider();
  if (options.signedIn !== false) await provider.login();
  const view = render(
    <AuthProviderTree provider={provider}>
      <OrganizationProvider>
        <MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }} initialEntries={[path]}>
          <AssistantProvider>
            <AppRoutes />
          </AssistantProvider>
        </MemoryRouter>
      </OrganizationProvider>
    </AuthProviderTree>,
  );
  return { provider, view };
}
