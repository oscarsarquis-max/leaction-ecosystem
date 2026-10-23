import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { ORG_A } from "./api/fixtures";
import { installApiMock, json } from "./test/fetchMock";
import { renderApp } from "./test/renderApp";

afterEach(() => {
  vi.unstubAllGlobals();
  localStorage.clear();
  sessionStorage.clear();
});

const QR = "https://www.nfce.fazenda.sp.gov.br/qrcode?p=352510000000000001916500100000000111000000015|3|1";

describe("leitura de QR da NFC-e", () => {
  it("consulta o código e não grava a nota", async () => {
    const user = userEvent.setup();
    installApiMock({
      "/fiscal/qr/read": () =>
        json({
          data: {
            recognized: true,
            import_available: false,
            model_label: "NFC-e",
            uf: "SP",
            environment: "producao",
            number: "1",
            series: "1",
            access_key: "352510000000000001916500100000000111000000015",
            message: "Consulta disponível; importação automática indisponível nesta origem.",
            consultation_url: QR,
            items: [],
          },
        }),
    });
    localStorage.setItem("panne.activeOrganization", ORG_A);
    await renderApp("/gestao/compras/entradas/nova?origem=qr");

    expect(await screen.findByRole("heading", { name: "Leia o QR Code da nota" })).toBeInTheDocument();
    await user.type(screen.getByLabelText("Colar endereço do QR Code"), QR);
    await user.click(screen.getByRole("button", { name: "Consultar código" }));
    expect(
      await screen.findByText(/importação automática indisponível nesta origem/),
    ).toBeInTheDocument();
    expect(screen.queryByText(/Nota gravada/)).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Continuar preenchendo a nota" }));
    await waitFor(() => {
      expect(screen.getByLabelText("Chave de acesso")).toHaveValue(
        "352510000000000001916500100000000111000000015",
      );
    });
    expect(screen.queryByText(/Nota gravada/)).not.toBeInTheDocument();
  });
});
