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
            dependency:
              "Os itens dependem do webservice oficial de download do XML da NFC-e, que exige certificado digital e-CNPJ do contribuinte.",
            consultation_url: QR,
            items: [],
          },
        }),
    });
    localStorage.setItem("panne.activeOrganization", ORG_A);
    await renderApp("/gestao/compras/entradas/nova?origem=qr");

    expect(await screen.findByRole("heading", { name: "Leia o QR Code da nota" })).toBeInTheDocument();
    await user.type(screen.getByLabelText("Colar endereço do QR Code"), QR);
    await user.click(screen.getByRole("button", { name: "Ler código" }));
    expect(
      await screen.findByText(/importação automática indisponível nesta origem/),
    ).toBeInTheDocument();
    expect(screen.getByText(/certificado digital/)).toBeInTheDocument();
    expect(screen.queryByText(/Nota gravada/)).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Preencher a nota com esta chave" }));
    await waitFor(() => {
      expect(screen.getByLabelText("Chave de acesso")).toHaveValue(
        "352510000000000001916500100000000111000000015",
      );
    });
    expect(screen.queryByText(/Nota gravada/)).not.toBeInTheDocument();
    expect(screen.getByText(/importação da nota não foi feita/)).toBeInTheDocument();
  });

  it("abre a nota existente da organização e não grava outra", async () => {
    const user = userEvent.setup();
    installApiMock({
      "/fiscal/qr/read": () =>
        json({
          data: {
            recognized: true,
            import_available: false,
            modality: "leitura_chave",
            items: [],
            model_label: "NFC-e",
            uf: "SP",
            environment_label: "produção",
            emission_label: "online",
            message: "Consulta disponível; importação automática indisponível nesta origem.",
            existing_document_id: "doc-da-organizacao",
          },
        }),
    });
    localStorage.setItem("panne.activeOrganization", ORG_A);
    await renderApp("/gestao/compras/entradas/nova?origem=qr");
    await user.type(await screen.findByLabelText("Colar endereço do QR Code"), QR);
    await user.click(screen.getByRole("button", { name: "Ler código" }));
    const open = await screen.findByRole("link", { name: "Abrir a nota" });
    expect(open).toHaveAttribute("href", "/gestao/compras/entradas/doc-da-organizacao");
    expect(screen.queryByRole("button", { name: "Preencher a nota com esta chave" })).not.toBeInTheDocument();
    expect(screen.queryByText(/Nota gravada/)).not.toBeInTheDocument();
  });

  it("conserva o endereço quando a câmera é negada e encerra ao cancelar", async () => {
    const user = userEvent.setup();
    const stop = vi.fn();
    const getUserMedia = vi.fn().mockRejectedValueOnce(new Error("negada")).mockResolvedValue({
      getTracks: () => [{ stop }],
    });
    Object.defineProperty(navigator, "mediaDevices", { configurable: true, value: { getUserMedia } });
    HTMLMediaElement.prototype.play = vi.fn().mockResolvedValue(undefined);
    vi.stubGlobal("BarcodeDetector", undefined);
    installApiMock({});
    localStorage.setItem("panne.activeOrganization", ORG_A);
    await renderApp("/gestao/compras/entradas/nova?origem=qr");
    const field = await screen.findByLabelText("Colar endereço do QR Code");
    await user.type(field, "https://www.nfce.fazenda.sp.gov.br/qrcode?p=1");
    await user.click(screen.getByRole("button", { name: "Usar câmera" }));
    expect(await screen.findByText(/não foi permitida/)).toBeInTheDocument();
    expect(field).toHaveValue("https://www.nfce.fazenda.sp.gov.br/qrcode?p=1");
    await user.click(screen.getByRole("button", { name: "Usar câmera" }));
    expect(await screen.findByText(/não lê QR sozinho/)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Cancelar" }));
    expect(stop).toHaveBeenCalled();
    expect(await screen.findByText("Aguardando o código ou o endereço.")).toBeInTheDocument();
    expect(field).toHaveValue("https://www.nfce.fazenda.sp.gov.br/qrcode?p=1");
  });

  it("não consulta de novo quando a câmera repete o mesmo código", async () => {
    const user = userEvent.setup();
    let reads = 0;
    installApiMock({
      "/fiscal/qr/read": () => {
        reads += 1;
        return json({
          data: {
            recognized: true,
            import_available: false,
            items: [],
            model_label: "NFC-e",
            message: "Consulta disponível; importação automática indisponível nesta origem.",
            dependency: "Os itens dependem do certificado digital.",
          },
        });
      },
    });
    const stop = vi.fn();
    Object.defineProperty(navigator, "mediaDevices", {
      configurable: true,
      value: { getUserMedia: vi.fn().mockResolvedValue({ getTracks: () => [{ stop }] }) },
    });
    HTMLMediaElement.prototype.play = vi.fn().mockResolvedValue(undefined);
    class Detector {
      detect() {
        return Promise.resolve([{ rawValue: QR }]);
      }
    }
    vi.stubGlobal("BarcodeDetector", Detector);
    localStorage.setItem("panne.activeOrganization", ORG_A);
    await renderApp("/gestao/compras/entradas/nova?origem=qr");
    await user.click(await screen.findByRole("button", { name: "Usar câmera" }));
    expect(await screen.findByText(/importação automática indisponível nesta origem/)).toBeInTheDocument();
    await new Promise((resolve) => setTimeout(resolve, 700));
    expect(reads).toBe(1);
    expect(stop).toHaveBeenCalled();
    expect(screen.queryByText(/Nota gravada/)).not.toBeInTheDocument();
  });
});
