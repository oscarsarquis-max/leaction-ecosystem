import { screen, waitFor } from "@testing-library/react";
import type { UserEvent } from "@testing-library/user-event";
import { expect } from "vitest";

/** Dev AccessGate: click Entrar before asserting app UI. */
export async function enterApp(user: UserEvent) {
  await waitFor(() => expect(screen.getByTestId("login-cta")).toBeInTheDocument());
  await user.click(screen.getByTestId("login-cta"));
}
