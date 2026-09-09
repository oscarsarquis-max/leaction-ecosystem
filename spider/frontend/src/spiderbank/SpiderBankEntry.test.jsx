import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen, fireEvent, waitFor, cleanup } from "@testing-library/react";
import { readFileSync } from "fs";
import { dirname, join } from "path";
import { fileURLToPath } from "url";
import SpiderBankEntry from "./SpiderBankEntry.jsx";
import ContextualLinkPresentation from "./ContextualLinkPresentation.jsx";
import { isGenericGatewayHref, opaqueContextIdFromLocation } from "./api.js";
import { arrivalNarrative, directArrivalNarrative } from "./arrivalCopy.js";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

const partnerHtml = readFileSync(
  join(dirname(fileURLToPath(import.meta.url)), "../../public/partner/agro-hoje/index.html"),
  "utf8",
);
const bankCss = readFileSync(join(dirname(fileURLToPath(import.meta.url)), "spiderbank.css"), "utf8");
const TECHNICAL_FIRST_FOLD = /MOCK_ONLY|SIMULATED_INFRASTRUCTURE|fingerprint|Intent|Policy|Capabilities|Routes|Data Plane|clickId|contextId/i;

function mockEntry(overrides = {}) {
  const entry = {
    partnerPublicName: "CampoAberto",
    gatewayUrl: "http://127.0.0.1:8080/go",
    statusLabel: "CONTEXTO CAPTURADO",
    click: {
      clickId: "clk-1",
      contextId: "ctx-1",
      createdAt: "2026-09-09T14:00:00Z",
    },
    page: {
      sourceTitle: "Quebra de safra aperta o caixa e obriga produtores a buscar recursos para manter o próximo ciclo | CampoAberto",
      sourceUrl: "http://127.0.0.1:8080/demo/partner/agro-hoje",
      contentFingerprint: "sha256:abc",
      acquisitionStatus: "CAPTURED",
    },
    provenance: [
      {
        order: 1,
        code: "LINK_CLICKED",
        label: "Link clicado",
        occurredAt: "2026-09-09T14:00:00Z",
        status: "OK",
        detail: "http://127.0.0.1:8080/go",
      },
    ],
    ...overrides,
  };
  const needAmount = {
    status: "NEED_AMOUNT",
    human: {
      headline: "O que o Spider entendeu",
      objective:
        "Perdi parte da safra, tenho compromissos vencendo e preciso de recursos para preparar o próximo plantio.",
      understanding:
        "Você precisa de recursos para atravessar este momento, honrar compromissos e preparar o próximo plantio.",
      policy: "A política contextual permite continuar. Ainda precisamos de uma informação.",
      missing: { key: "amount", question: "De quanto você precisa?" },
      cropFailureNoted: true,
      path: null,
      capabilities: [],
    },
    technical: {
      intent: "SEEK_WORKING_CAPITAL",
      domain: "CREDIT",
      purpose: "PRODUCTION_CONTINUITY",
      economicContext: "CROP_FAILURE",
      economicContextSources: ["PAGE_CONTEXT", "USER_OBJECTIVE"],
      amount: null,
      amountInvented: false,
      cropFailureFromLink: false,
      decisionId: "ctxd-1",
      pageUsed: true,
      pageTitle: "Quebra de safra pressiona produtores",
      directEntry: false,
      confidence: 0.94,
      contextProvenance: "CONTEXTUAL_LINK",
    },
    principle:
      "O Contextual Link fornece contexto de origem, mas não define a intenção. O objetivo pertence ao usuário.",
  };
  const understood = {
    ...needAmount,
    status: "UNDERSTOOD",
    human: {
      ...needAmount.human,
      missing: null,
      path: {
        title: "Para ajudar você, o Spider precisa:",
        honest: "Nenhuma contratação, taxa, prazo ou desembolso acontece nesta demonstração.",
        steps: [
          { capabilityId: "IDENTIFY_CUSTOMER", name: "Identificar cliente", state: "já resolvido" },
          {
            capabilityId: "GET_CUSTOMER_PROFILE",
            name: "Consultar perfil do cliente",
            state: "ainda não disponível",
          },
        ],
      },
    },
    technical: { ...needAmount.technical, amount: "80000", amountSource: "USER_PROVIDED" },
  };
  vi.stubGlobal(
    "fetch",
    vi.fn().mockImplementation((url, init) => {
      if (String(url).includes("/v1/demo/spiderbank/understand")) {
        const body = init?.body ? JSON.parse(init.body) : {};
        const payload = body.amount ? understood : needAmount;
        return Promise.resolve({ ok: true, json: async () => payload });
      }
      return Promise.resolve({ ok: true, json: async () => entry });
    }),
  );
}

describe("partner news page", () => {
  it("keeps CampoAberto editorial identity and a premium wine advertisement", () => {
    expect(partnerHtml).toContain("CampoAberto");
    expect(partnerHtml).toContain("Quebra de safra aperta o caixa e obriga produtores a buscar recursos");
    expect(partnerHtml).toContain("Receita cai, mas o próximo ciclo não espera");
    expect(partnerHtml).toContain("Produtores tentam preservar capital de giro");
    expect(partnerHtml).toContain("Decisões precisam ser tomadas antes da nova safra");
    expect(partnerHtml).toContain("Portal independente");
    expect(partnerHtml).toContain('href="http://127.0.0.1:8080/go"');
    expect(partnerHtml).not.toContain("href=\"http://127.0.0.1:8080/go?");
    expect(partnerHtml).not.toMatch(/intent=/i);
    expect(partnerHtml).not.toMatch(/campaign=/i);
    expect(partnerHtml).not.toMatch(/contextId=/i);
    expect(partnerHtml).not.toMatch(/purpose=/i);
    expect(partnerHtml).not.toMatch(/cropFailure=/i);
    expect(partnerHtml).toContain("NENHUM");
    expect(partnerHtml).toContain("INEXISTENTE ANTES DO CLIQUE");
    expect(partnerHtml).toContain("Provar link genérico");
    expect(partnerHtml).not.toContain("--accent: #3dd6c6");
    expect(partnerHtml).not.toMatch(/MOCK_ONLY|SIMULATED_INFRASTRUCTURE/);
    expect(partnerHtml).not.toMatch(/lorem ipsum/i);
    expect(partnerHtml).toContain("Banco Contextual");
    expect(partnerHtml).toContain("Sua produção precisa continuar");
    expect(partnerHtml).toContain("atravessar um momento de pressão financeira");
    expect(partnerHtml).toMatch(/Conheça suas opções/i);
    expect(partnerHtml).toContain('target="_blank"');
    expect(partnerHtml).toContain("#7c2748");
    expect(partnerHtml).not.toMatch(/FNE Giro|taxa de [\d]|contratar agora/i);
  });
});

describe("SpiderBank identity", () => {
  it("uses wine, off-white and rose in an editorial composition without console neon", () => {
    expect(bankCss).toMatch(/#7c2748/i);
    expect(bankCss).toContain("#f7f3f1");
    expect(bankCss).toContain("#ead4dc");
    expect(bankCss).toContain("min-height: calc(100vh");
    expect(bankCss).toContain(".sb-fold");
    expect(bankCss).toContain(".sb-chapter");
    expect(bankCss).not.toContain("#3dd6c6");
    expect(bankCss).toContain("@media (max-width: 860px)");
    expect(bankCss).toContain("prefers-reduced-motion");
  });
});

describe("generic link helper", () => {
  it("accepts /go without contextual query", () => {
    expect(isGenericGatewayHref("http://127.0.0.1:8080/go")).toBe(true);
    expect(isGenericGatewayHref("http://127.0.0.1:8080/go?intent=x")).toBe(false);
  });

  it("requires opaque ctx token", () => {
    expect(opaqueContextIdFromLocation("?ctx=ctx-abc")).toBe("ctx-abc");
    expect(opaqueContextIdFromLocation("?ctx=quebra-safra")).toBe(null);
  });
});

describe("arrival copy", () => {
  it("describes crop-failure context without assuming the client wants working capital", () => {
    const copy = arrivalNarrative({
      acquisitionStatus: "CAPTURED",
      sourceTitle: "Quebra de safra pressiona produtores",
    });
    expect(copy.lead).toMatch(/quebra de safra/i);
    expect(copy.lead).not.toMatch(/capital de giro|FNE|empréstimo/i);
    expect(copy.status).toBe("Já sabemos de onde você veio.");
  });

  it("does not invent CampoAberto on a direct SpiderBank visit", () => {
    const copy = directArrivalNarrative();
    expect(copy.lead).toMatch(/chegou diretamente/i);
    expect(copy.partnerName).toBeNull();
    expect(copy.direct).toBe(true);
  });
});

describe("SpiderBank landing", () => {
  it("opens as Banco Contextual with an editorial first fold", async () => {
    mockEntry();
    window.history.pushState({}, "", "/spiderbank/entry?ctx=ctx-1");
    render(<SpiderBankEntry />);
    const hero = await screen.findByTestId("spiderbank-hero");
    expect(hero).toHaveTextContent("Banco Contextual");
    expect(hero).toHaveTextContent("Um banco que");
    expect(hero).toHaveTextContent("entende primeiro");
    expect(hero.textContent).not.toMatch(TECHNICAL_FIRST_FOLD);
    expect(screen.getByTestId("fold-moment")).toHaveTextContent("Já sabemos de onde você veio");
    expect(screen.getByTestId("origin-context")).toHaveTextContent("Seu momento");
    expect(screen.getByTestId("objective-block")).toHaveTextContent("Seu objetivo");
    expect(screen.getByTestId("path-block")).toHaveTextContent("Seu caminho");
    expect(screen.getByTestId("arrival-lead")).toHaveTextContent("quebra de safra");
    expect(screen.getByTestId("context-status")).toHaveTextContent("Já sabemos de onde você veio");
    expect(screen.getByTestId("context-is-not-intent")).toHaveTextContent(
      "Conhecer o contexto não significa presumir",
    );
    expect(screen.getByTestId("objective-input")).toHaveAttribute(
      "placeholder",
      expect.stringMatching(/Perdi parte da safra/),
    );
    expect(screen.getByTestId("understand-objective")).toBeDisabled();
    expect(screen.getByTestId("understand-objective")).toHaveTextContent(/entender meu objetivo/i);
    expect(screen.queryByTestId("provenance-panel")).not.toBeInTheDocument();
    expect(screen.queryByLabelText(/cpf|cnpj/i)).not.toBeInTheDocument();
    expect(screen.getByTestId("journey-entendimento")).not.toHaveClass("is-done");
    expect(screen.getByTestId("journey-caminho")).not.toHaveClass("is-done");
  });

  it("calls Context Intelligence when the client asks to understand the objective", async () => {
    mockEntry();
    window.history.pushState({}, "", "/spiderbank/entry?ctx=ctx-1");
    render(<SpiderBankEntry />);
    await screen.findByTestId("objective-input");
    fireEvent.change(screen.getByTestId("objective-input"), {
      target: {
        value:
          "Perdi parte da safra, tenho compromissos vencendo e preciso de recursos para preparar o próximo plantio.",
      },
    });
    fireEvent.click(screen.getByTestId("understand-objective"));
    expect(await screen.findByTestId("understanding-block")).toHaveTextContent("quebra de safra");
    expect(screen.getByTestId("missing-amount")).toHaveTextContent("De quanto você precisa");
    expect(screen.getByTestId("amount-input")).toHaveValue("");
    expect(screen.getByTestId("journey-entendimento")).toHaveClass("is-done");
    expect(screen.getByTestId("journey-caminho")).not.toHaveClass("is-done");
    expect(
      fetch.mock.calls.some((call) => String(call[0]).includes("/v1/demo/spiderbank/understand")),
    ).toBe(true);
    fireEvent.click(screen.getByTestId("open-understanding"));
    expect(screen.getByTestId("economic-context")).toHaveTextContent("CROP_FAILURE");
    expect(screen.getByTestId("crop-failure-source")).toHaveTextContent("PAGE_CONTEXT");
    expect(screen.getByTestId("crop-from-link")).toHaveTextContent("NÃO");

    fireEvent.change(screen.getByTestId("amount-input"), { target: { value: "80000" } });
    fireEvent.click(screen.getByTestId("continue-with-amount"));
    expect(await screen.findByTestId("human-path")).toHaveTextContent("Identificar cliente");
    expect(screen.getByTestId("journey-caminho")).toHaveClass("is-done");
    const understandBodies = fetch.mock.calls
      .filter((call) => String(call[0]).includes("/understand"))
      .map((call) => JSON.parse(call[1].body));
    expect(understandBodies[0].amount).toBeUndefined();
    expect(understandBodies[1].amount).toBe("80000");
  });

  it("keeps DEMO-001 proof inside a drawer, not on the first fold", async () => {
    mockEntry();
    window.history.pushState({}, "", "/spiderbank/entry?ctx=ctx-1");
    render(<SpiderBankEntry />);
    await screen.findByTestId("open-provenance");
    fireEvent.click(screen.getByTestId("open-provenance"));
    await waitFor(() => expect(screen.getByTestId("provenance-panel")).toBeInTheDocument());
    expect(screen.getByTestId("provenance-panel")).toHaveTextContent("Como este contexto nasceu");
    expect(screen.getByTestId("context-id")).toHaveTextContent("ctx-1");
    expect(screen.getByTestId("click-id")).toHaveTextContent("clk-1");
    expect(screen.getByTestId("before-click")).toHaveTextContent("INEXISTENTE");
    expect(screen.getByTestId("after-click")).toHaveTextContent("sha256:abc");
    expect(screen.getByTestId("proof-origin")).toHaveTextContent("CampoAberto");
    expect(screen.getByTestId("source-title")).toHaveTextContent(/Quebra de safra aperta o caixa/i);
    expect(screen.getByTestId("fingerprint")).toHaveTextContent("sha256:abc");
    expect(screen.getByTestId("provenance-step-LINK_CLICKED")).toHaveTextContent("Link clicado");
  });

  it("explains missing referrer without inventing a page", async () => {
    mockEntry({
      statusLabel: "CONTEXTO MÍNIMO — ORIGEM NÃO ADQUIRIDA",
      click: { clickId: "clk-2", contextId: "ctx-2", createdAt: "2026-09-09T14:00:01Z" },
      page: { sourceTitle: "", sourceUrl: "", contentFingerprint: "", acquisitionStatus: "UNAVAILABLE" },
      provenance: [],
    });
    window.history.pushState({}, "", "/spiderbank/entry?ctx=ctx-2");
    render(<SpiderBankEntry />);
    expect(await screen.findByTestId("context-status")).toHaveTextContent("origem não identificada");
    expect(screen.getByTestId("origin-title")).toHaveTextContent("não adquirida");
  });

  it("shows a direct bank entry without partner context", () => {
    window.history.pushState({}, "", "/spiderbank");
    render(<SpiderBankEntry />);
    expect(screen.getByTestId("spiderbank-hero")).toHaveTextContent("entende primeiro");
    expect(screen.getByTestId("direct-entry")).toHaveTextContent("Conte-nos o que precisa resolver");
    expect(screen.getByTestId("objective-input")).toBeInTheDocument();
    expect(screen.queryByText("CampoAberto")).not.toBeInTheDocument();
    expect(screen.queryByTestId("open-provenance")).not.toBeInTheDocument();
  });

  it("does not invent crop failure on a direct visit with a production-only objective", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({
          status: "NEED_AMOUNT",
          human: {
            headline: "O que o Spider entendeu",
            understanding: "Você precisa de recursos para manter a sua produção. Não identificamos quebra de safra neste pedido.",
            policy: "A política contextual permite continuar.",
            missing: { key: "amount", question: "De quanto você precisa?" },
            cropFailureNoted: false,
          },
          technical: {
            economicContext: null,
            economicContextSources: [],
            cropFailureFromLink: false,
            directEntry: true,
            contextProvenance: "DIRECT_ENTRY",
            pageUsed: false,
            decisionId: "ctxd-direct",
            intent: "SEEK_WORKING_CAPITAL",
            purpose: "PRODUCTION_CONTINUITY",
          },
        }),
      }),
    );
    window.history.pushState({}, "", "/spiderbank");
    render(<SpiderBankEntry />);
    fireEvent.change(screen.getByTestId("objective-input"), {
      target: { value: "Preciso de recursos para manter minha produção." },
    });
    fireEvent.click(screen.getByTestId("understand-objective"));
    expect(await screen.findByTestId("understanding-copy")).toHaveTextContent("Não identificamos quebra de safra");
    expect(screen.getByTestId("crop-failure-absent")).toHaveTextContent("CROP_FAILURE ausente");
    fireEvent.click(screen.getByTestId("open-understanding"));
    expect(screen.getByTestId("economic-context")).toHaveTextContent("AUSENTE");
    expect(screen.getByTestId("context-provenance")).toHaveTextContent("DIRECT_ENTRY");
  });
});

describe("Experience Hub entry", () => {
  it("presents Spider as a contextual platform and starts CampoAberto without a script", () => {
    render(<ContextualLinkPresentation />);
    expect(screen.getByTestId("experience-hub")).toBeInTheDocument();
    expect(screen.getByTestId("open-partner")).toHaveAttribute(
      "href",
      "http://127.0.0.1:8080/demo/partner/agro-hoje",
    );
    expect(screen.getByTestId("open-partner")).toHaveAttribute("target", "_blank");
    expect(screen.getByTestId("open-spiderbank")).toHaveAttribute("href", "/spiderbank");
    expect(screen.getByTestId("open-console")).toHaveAttribute("href", "/console");
    expect(screen.getByTestId("hub-cta-try")).toHaveTextContent(/^Experimentar$/);
    expect(screen.queryByTestId("presentation-script")).not.toBeInTheDocument();
    expect(screen.getByTestId("experience-hub")).not.toHaveTextContent("Passo 1");
    expect(screen.getByTestId("experience-hub")).toHaveTextContent("Banco Contextual");
  });
});
