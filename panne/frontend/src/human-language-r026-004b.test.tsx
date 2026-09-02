import { render, screen, waitFor } from "@testing-library/react";
import { StrictMode } from "react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import { AppRoutes } from "./App";
import { ApiError, isCancelledError } from "./api/errors";
import { DOSSIER_ID, ORDER_ID, PLAN_ID } from "./api/fixtures";
import { AssistantProvider } from "./assistant/AssistantContext";
import { AuthProviderTree } from "./auth/AuthContext";
import { FakeAuthProvider } from "./auth/FakeAuthProvider";
import { ErrorState } from "./components/Feedback";
import {
  completenessLabel,
  dossierStatusLabel,
  evidenceResultLabel,
  nutrientLabel,
} from "./language/labeling";
import { aggregateBalancesByUnit } from "./language/inventory";
import { formatOperationalQuantity } from "./language/quantities";
import { OrganizationProvider } from "./session/OrganizationContext";
import { installApiMock, json } from "./test/fetchMock";
import { renderApp } from "./test/renderApp";

afterEach(() => {
  vi.unstubAllGlobals();
  localStorage.clear();
  sessionStorage.clear();
});

async function renderStrict(path: string) {
  const provider = new FakeAuthProvider();
  await provider.login();
  return render(
    <StrictMode>
      <AuthProviderTree provider={provider}>
        <OrganizationProvider>
          <MemoryRouter
            future={{ v7_relativeSplatPath: true }}
            initialEntries={[path]}
          >
            <AssistantProvider>
              <AppRoutes />
            </AssistantProvider>
          </MemoryRouter>
        </OrganizationProvider>
      </AuthProviderTree>
    </StrictMode>,
  );
}

describe("R026-004 cancelamento concorrente", () => {
  it("isCancelledError reconhece ApiError cancelado e AbortError", () => {
    expect(isCancelledError(new ApiError("cancelado", "A consulta anterior foi substituída.", 0))).toBe(true);
    expect(isCancelledError(Object.assign(new Error("aborted"), { name: "AbortError" }))).toBe(true);
    expect(isCancelledError(new ApiError("rede", "falha", 0))).toBe(false);
  });

  it("ErrorState não apresenta cancelamento como falha", () => {
    render(<ErrorState error={new ApiError("cancelado", "A consulta anterior foi substituída.", 0)} />);
    expect(screen.queryByRole("heading", { name: /Não foi possível carregar/ })).not.toBeInTheDocument();
    expect(screen.queryByText(/consulta anterior foi substituída/i)).not.toBeInTheDocument();
    expect(screen.getByRole("status")).toHaveTextContent(/Carregando/);
  });

  it("rastreabilidade sob StrictMode tolera cancelamento inicial", async () => {
    let calls = 0;
    installApiMock({
      [`/orders/${ORDER_ID}/traceability`]: () => {
        calls += 1;
        if (calls === 1) {
          throw new ApiError("cancelado", "A consulta anterior foi substituída.", 0);
        }
        return json({
          data: {
            order: {
              id: ORDER_ID,
              public_code: "ORD-20260824-0004",
              status: "in_progress",
              formulation_version_id: null,
              scale_calculation_id: null,
              materials_hash: "a".repeat(64),
              steps_hash: "b".repeat(64),
              snapshot_hash: "c".repeat(64),
              policy_hash: null,
            },
            batches: [],
            planned_materials: [],
            planned_steps: [],
            actual_materials: [],
            weighings: [],
            verifications: [],
            consumptions: [],
            step_runs: [],
            yields: [],
            occurrences: [],
            dependencies: [],
            overrides: [],
            sheet_issues: [],
            events: [
              {
                id: "e1",
                type: "order.released",
                command: "release",
                occurred_at: "2026-08-24T10:00:00+00:00",
              },
            ],
          },
        });
      },
    });
    await renderStrict(`/rastreabilidade/${ORDER_ID}`);
    expect(await screen.findByRole("heading", { name: /Rastreabilidade ORD-20260824-0004/ })).toBeInTheDocument();
    await waitFor(() => {
      expect(screen.queryByText(/consulta anterior foi substituída/i)).not.toBeInTheDocument();
    });
  });

  it("plano mostra nome do produto sem rótulo artificial", async () => {
    installApiMock();
    await renderApp(`/planejamento/${PLAN_ID}`);
    expect(await screen.findAllByText("Pão francês")).not.toHaveLength(0);
    expect(screen.queryByText(/Produto técnico/)).not.toBeInTheDocument();
  });

  it("erro real continua visível", async () => {
    installApiMock({
      [`/orders/${ORDER_ID}/traceability`]: () => {
        throw new ApiError("rede", "Não foi possível contactar a API.", 0);
      },
    });
    await renderApp(`/rastreabilidade/${ORDER_ID}`);
    expect(await screen.findByRole("heading", { name: /Não foi possível carregar/ })).toBeInTheDocument();
  });
});

describe("R026-004-b estoque", () => {
  it("agrega por unidade e não mistura g com un", () => {
    const totals = aggregateBalancesByUnit([
      { physical_quantity: "1500.000000", reserved_quantity: "0", available_quantity: "1500", unit_code: "g" },
      { physical_quantity: "120", reserved_quantity: "10", available_quantity: "110", unit_code: "un" },
    ]);
    expect(totals).toHaveLength(2);
    expect(totals.find((row) => row.unit === "g")?.physical).toBe(1500);
    expect(totals.find((row) => row.unit === "un")?.available).toBe(110);
  });

  it("visão geral formata sem seis casas e com unidade", async () => {
    installApiMock();
    await renderApp("/componentes/estoque");
    expect(await screen.findByRole("heading", { name: "Estoque" })).toBeInTheDocument();
    expect(screen.getByText(/Unidade: g/)).toBeInTheDocument();
    expect(screen.getByText(/Unidade: un/)).toBeInTheDocument();
    expect(screen.getAllByText(formatOperationalQuantity("1500", "g")).length).toBeGreaterThan(0);
    expect(document.body.textContent).not.toMatch(/1500\.000000/);
  });
});

describe("R026-004-c dossiê", () => {
  it("lista usa nome da receita e estado humano, sem UUID truncado", async () => {
    installApiMock();
    await renderApp("/conformidade/dossies");
    expect(await screen.findByText("Pão francês")).toBeInTheDocument();
    expect(screen.getByText("Avaliado")).toBeInTheDocument();
    expect(screen.queryByText(/Dossiê [0-9a-f]{8}/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/\bevaluated\b/)).not.toBeInTheDocument();
  });

  it("detalhe traduz nutrientes e completude", async () => {
    installApiMock();
    await renderApp(`/conformidade/dossies/${DOSSIER_ID}`);
    expect(await screen.findByRole("heading", { name: /Dossiê de rotulagem/ })).toBeInTheDocument();
    expect(screen.getByText(/Completude:\s*Completo/)).toBeInTheDocument();
    expect(screen.getAllByText(nutrientLabel("energy_kcal")).length).toBeGreaterThan(0);
    expect(screen.queryByText(/\bincomplete\b/)).not.toBeInTheDocument();
    expect(dossierStatusLabel("evaluated")).toBe("Avaliado");
    expect(completenessLabel("incomplete")).toBe("Incompleto");
    expect(evidenceResultLabel("manual_review_required")).toBe("Revisão humana necessária");
  });
});
