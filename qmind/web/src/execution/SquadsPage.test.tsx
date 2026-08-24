import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { SquadsPage } from "@/execution/SquadsPage";
import { resetQmindClient } from "@/api/qmindApi";
import { resetConfigCache } from "@/config/env";
import { enterApp } from "@/test/enterApp";
import {
  bodyOf,
  executionQueryKeys,
  expectNoVisibleUuid,
  jsonResponse,
  membershipResponse,
  methodOf,
  optionLabels,
  ORG_ID,
  orgMemberPayload,
  OWNER_ID,
  renderExecution,
  squadPayload,
  SQUAD_ID,
  stubMatchMedia,
  urlOf,
} from "@/test/executionHarness";

const SECOND_MEMBER_ID = "66666666-6666-4666-8666-666666666666";
const ROUTE = "/execution/squads";

type Call = { url: string; method: string; body: unknown };
const calls: Call[] = [];

type Router = (
  input: RequestInfo | URL,
  init?: RequestInit,
) => Response | Promise<Response> | undefined;

function installFetch(router?: Router, squads: unknown[] = []) {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = urlOf(input);
      const method = methodOf(input, init);
      calls.push({ url, method, body: await bodyOf(input, init) });

      const custom = await router?.(input, init);
      if (custom) return custom;

      if (url.includes("/organizations/me/memberships")) return membershipResponse();
      if (url.includes("/organizations/current/members")) {
        return jsonResponse([
          orgMemberPayload(),
          orgMemberPayload({
            membership_id: SECOND_MEMBER_ID,
            display_name: "Bruno Costa",
            email: "bruno@example.com",
            roles: ["process_owner"],
          }),
        ]);
      }
      if (url.includes("/agile/squads/") && url.includes("/memberships")) {
        return method === "POST"
          ? jsonResponse({ id: "sm-1" }, 201)
          : jsonResponse([
              {
                id: "sm-1",
                organization_id: ORG_ID,
                squad_id: SQUAD_ID,
                membership_id: OWNER_ID,
                agile_role: "value_owner",
                status: "active",
                member_display_name: "Ana Silva",
                member_email: "ana@example.com",
                created_by: OWNER_ID,
                created_at: new Date().toISOString(),
                updated_at: new Date().toISOString(),
              },
            ]);
      }
      if (url.includes("/agile/squads")) {
        return method === "POST"
          ? jsonResponse(squadPayload(), 201)
          : jsonResponse(squads);
      }
      return jsonResponse({}, 404);
    }),
  );
}

async function openCreateForm(user: ReturnType<typeof userEvent.setup>) {
  renderExecution(<SquadsPage />, { path: ROUTE });
  await enterApp(user);
  await waitFor(() =>
    expect(screen.getByTestId("squad-create-form")).toBeInTheDocument(),
  );
}

describe("SquadsPage", () => {
  beforeEach(() => {
    calls.length = 0;
    resetConfigCache();
    resetQmindClient();
    vi.stubGlobal("matchMedia", vi.fn(stubMatchMedia(false)));
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("offers value owners by display name, never by identifier", async () => {
    installFetch();
    const user = userEvent.setup();
    await openCreateForm(user);

    const select = screen.getByLabelText(/Dono de valor/i);
    await waitFor(() =>
      expect(optionLabels(select).join(" ")).toContain("Ana Silva"),
    );
    const labels = optionLabels(select).join(" ");
    expect(labels).toContain("Bruno Costa");
    expect(labels).not.toMatch(/[0-9a-f]{8}-[0-9a-f]{4}/i);
    expectNoVisibleUuid();
  });

  it("creates squad and value owner in a single transactional request", async () => {
    installFetch();
    const user = userEvent.setup();
    await openCreateForm(user);

    await user.type(screen.getByLabelText(/Nome da squad/i), "Squad Qualidade");
    const select = screen.getByLabelText(/Dono de valor/i);
    await waitFor(() =>
      expect(optionLabels(select).join(" ")).toContain("Bruno Costa"),
    );
    await user.selectOptions(select, SECOND_MEMBER_ID);
    await user.click(screen.getByRole("button", { name: /Criar squad/i }));

    await waitFor(() =>
      expect(
        calls.some((c) => c.url.includes("/agile/squads") && c.method === "POST"),
      ).toBe(true),
    );
    const posted = calls.filter(
      (c) => c.url.includes("/agile/squads") && c.method === "POST",
    );
    expect(posted).toHaveLength(1);
    expect(posted[0].body).toMatchObject({
      name: "Squad Qualidade",
      value_owner_membership_id: SECOND_MEMBER_ID,
    });
  });

  it("blocks submission until a value owner is chosen", async () => {
    installFetch();
    const user = userEvent.setup();
    await openCreateForm(user);

    await user.type(screen.getByLabelText(/Nome da squad/i), "Squad sem dono");
    expect(screen.getByRole("button", { name: /Criar squad/i })).toBeDisabled();
    expect(
      calls.some((c) => c.url.includes("/agile/squads") && c.method === "POST"),
    ).toBe(false);
  });

  it("hides the create form for reader-only profiles", async () => {
    installFetch((input) => {
      if (urlOf(input).includes("/organizations/me/memberships")) {
        return membershipResponse(["reader"]);
      }
      return undefined;
    }, [squadPayload()]);
    const user = userEvent.setup();
    renderExecution(<SquadsPage />, { path: ROUTE });
    await enterApp(user);

    await waitFor(() =>
      expect(screen.getByText("Squad Qualidade")).toBeInTheDocument(),
    );
    expect(screen.queryByTestId("squad-create-form")).toBeNull();
    expect(screen.queryByRole("button", { name: /Criar squad/i })).toBeNull();
  });

  it("lists squad members by display name and scopes cache keys to the organization", async () => {
    installFetch(undefined, [squadPayload()]);
    const user = userEvent.setup();
    const { queryClient } = renderExecution(<SquadsPage />, { path: ROUTE });
    await enterApp(user);

    await waitFor(() =>
      expect(screen.getByText("Squad Qualidade")).toBeInTheDocument(),
    );
    await user.click(screen.getByRole("button", { name: "Membros" }));

    await waitFor(() =>
      expect(screen.getByText(/Ana Silva.*Dono de valor/)).toBeInTheDocument(),
    );
    expectNoVisibleUuid();

    const keys = executionQueryKeys(queryClient);
    expect(keys.length).toBeGreaterThan(0);
    for (const key of keys) {
      expect(key[1]).toBe(ORG_ID);
    }
    expect(keys.some((key) => key[3] === "squads")).toBe(true);
  });
});
