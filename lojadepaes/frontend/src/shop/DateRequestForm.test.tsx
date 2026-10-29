import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ApiError } from "../services/http";
import {
  DATE_REQUEST_EXPLANATION,
  DateRequestForm,
  QUANTITY_REQUIRED_MESSAGE,
  parseIntendedQuantity,
} from "./DateRequestForm";
import { fetchOperations } from "./operationsApi";
import { submitDateRequest } from "./suggestionsApi";

vi.mock("./operationsApi", () => ({
  fetchOperations: vi.fn(async () => ({
    preview_protection: false,
    orders_enabled: true,
    payments_enabled: true,
    date_requests_enabled: true,
    house_fidelity_active: true,
    business_date: "2026-10-01",
    closure_notice: null,
    message: null,
  })),
}));

vi.mock("./suggestionsApi", () => ({
  submitDateRequest: vi.fn(),
}));

vi.mock("./tracking", () => ({
  trackEvent: vi.fn(),
}));

const OPS = {
  preview_protection: false,
  orders_enabled: true,
  payments_enabled: true,
  date_requests_enabled: true,
  house_fidelity_active: true,
  business_date: "2026-10-01",
  closure_notice: null as string | null,
  message: null,
};

async function fillBase(user: ReturnType<typeof userEvent.setup>) {
  await user.clear(screen.getByLabelText("Data desejada"));
  await user.type(screen.getByLabelText("Data desejada"), "2026-10-22");
  await user.type(screen.getByLabelText("Nome"), "Bia");
  await user.type(screen.getByLabelText("E-mail"), "bia@example.com");
}

describe("DateRequestForm", () => {
  beforeEach(() => {
    sessionStorage.clear();
    vi.mocked(submitDateRequest).mockReset();
    vi.mocked(fetchOperations).mockResolvedValue({ ...OPS });
  });

  it("inicia quantidade vazia, sem 2 nem 1, e aceita um pão", async () => {
    const user = userEvent.setup();
    vi.mocked(submitDateRequest).mockResolvedValue({
      id: "req-1",
      status: "pending",
      desired_date: "2026-10-22",
      message: "Recebemos sua sugestão. Ainda não confirma a fornada.",
    });
    render(<DateRequestForm selectedDate={null} lines={[]} cartCount={0} />);
    const quantity = await screen.findByLabelText("Quantidade pretendida");
    expect((quantity as HTMLInputElement).value).toBe("");
    expect(quantity).toHaveAttribute("placeholder", "Informe quantos pães");
    expect(screen.getByText(DATE_REQUEST_EXPLANATION)).toBeInTheDocument();
    expect(screen.queryByText(/inclusive para hoje/i)).not.toBeInTheDocument();
    await fillBase(user);
    await user.type(quantity, "1");
    await user.click(screen.getByRole("button", { name: "Enviar solicitação" }));
    await waitFor(() => {
      expect(vi.mocked(submitDateRequest)).toHaveBeenCalledWith(
        expect.objectContaining({ intended_quantity: 1, desired_date: "2026-10-22" }),
      );
    });
  });

  it("rejeita vazio, zero, negativo e fracionário sem enviar", async () => {
    const user = userEvent.setup();
    render(<DateRequestForm selectedDate={null} lines={[]} cartCount={0} />);
    await screen.findByLabelText("Quantidade pretendida");
    await fillBase(user);
    await user.click(screen.getByRole("button", { name: "Enviar solicitação" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(QUANTITY_REQUIRED_MESSAGE);
    expect(screen.getByLabelText("Nome")).toHaveValue("Bia");
    expect(vi.mocked(submitDateRequest)).not.toHaveBeenCalled();

    for (const invalid of ["0", "-1", "1.5"]) {
      await user.clear(screen.getByLabelText("Quantidade pretendida"));
      await user.type(screen.getByLabelText("Quantidade pretendida"), invalid);
      await user.click(screen.getByRole("button", { name: "Enviar solicitação" }));
      expect(screen.getByRole("alert")).toHaveTextContent(QUANTITY_REQUIRED_MESSAGE);
      expect(screen.getByLabelText("Quantidade pretendida")).toHaveDisplayValue(invalid);
    }
    expect(vi.mocked(submitDateRequest)).not.toHaveBeenCalled();
  });

  it("mostra o aviso da Agenda só quando o formulário aparece isolado", async () => {
    const notice = "Recebemos pedidos para as fornadas disponíveis a partir de 21 de outubro.";
    vi.mocked(fetchOperations).mockResolvedValue({ ...OPS, closure_notice: notice });
    const { rerender } = render(
      <DateRequestForm
        selectedDate={null}
        lines={[]}
        cartCount={0}
        calendarReady
        closureNoticeVisibleAbove
      />,
    );
    await screen.findByLabelText("Data desejada");
    expect(screen.getByText(DATE_REQUEST_EXPLANATION)).toBeInTheDocument();
    expect(screen.queryByText(notice)).not.toBeInTheDocument();

    rerender(
      <DateRequestForm selectedDate={null} lines={[]} cartCount={0} calendarReady closureNoticeVisibleAbove={false} />,
    );
    expect(await screen.findByText(notice)).toBeInTheDocument();
  });

  it("mostra o formulário habilitado na primeira carga, sem clique", async () => {
    render(<DateRequestForm selectedDate={null} lines={[]} cartCount={0} />);
    expect(await screen.findByLabelText("Data desejada")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Precisa de outra data?" })).toBeInTheDocument();
    expect(screen.getByText(DATE_REQUEST_EXPLANATION)).toBeInTheDocument();
    expect(screen.queryByText(/Inclusive para hoje, você pode sugerir/)).not.toBeInTheDocument();
    expect(screen.queryByText(/Conte a data que você tem em mente/)).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Sugerir uma data" })).not.toBeInTheDocument();
    expect(screen.getByLabelText("Nome")).toBeInTheDocument();
    expect(screen.getByLabelText("E-mail")).toBeInTheDocument();
    expect(screen.getByLabelText("Quantidade pretendida")).toBeInTheDocument();
    expect(screen.getByLabelText("Mensagem (opcional)")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Enviar solicitação" })).toBeEnabled();
    expect(vi.mocked(submitDateRequest)).not.toHaveBeenCalled();
  });

  it("reaproveita nome e e-mail e usa a seleção no lugar da quantidade", async () => {
    sessionStorage.setItem("lojadepaes_contact", JSON.stringify({ name: "Ana", email: "ana@example.com" }));
    render(
      <DateRequestForm
        selectedDate="2026-10-08"
        lines={[{ kind: "product", variant_id: "v1", quantity: 2 }]}
        cartCount={2}
      />,
    );
    expect(await screen.findByLabelText("Data desejada")).toHaveValue("2026-10-08");
    expect(screen.getByLabelText("Nome")).toHaveValue("Ana");
    expect(screen.getByLabelText("E-mail")).toHaveValue("ana@example.com");
    expect(screen.queryByLabelText("Quantidade pretendida")).not.toBeInTheDocument();
    expect(screen.getByText("Vamos considerar os pães já escolhidos na sua seleção.")).toBeInTheDocument();
    expect(vi.mocked(submitDateRequest)).not.toHaveBeenCalled();
  });

  it("não aparece quando a solicitação está desligada", async () => {
    vi.mocked(fetchOperations).mockResolvedValueOnce({
      ...OPS,
      date_requests_enabled: false,
    });
    render(<DateRequestForm selectedDate={null} lines={[]} cartCount={0} />);
    await waitFor(() => {
      expect(vi.mocked(fetchOperations)).toHaveBeenCalled();
    });
    expect(screen.queryByText("Precisa de outra data?")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Enviar solicitação" })).not.toBeInTheDocument();
  });

  it("envia só no botão, mantém o formulário após sucesso e preserva campos no erro", async () => {
    const user = userEvent.setup();
    vi.mocked(submitDateRequest)
      .mockRejectedValueOnce(new ApiError(422, "essa data já passou"))
      .mockResolvedValueOnce({
        id: "req-1",
        status: "pending",
        desired_date: "2026-10-15",
        message: "Recebemos sua sugestão. Ainda não confirma a fornada.",
      });
    render(<DateRequestForm selectedDate={null} lines={[]} cartCount={0} />);
    await screen.findByLabelText("Data desejada");
    await user.clear(screen.getByLabelText("Data desejada"));
    await user.type(screen.getByLabelText("Data desejada"), "2026-10-15");
    await user.type(screen.getByLabelText("Nome"), "Bia");
    await user.type(screen.getByLabelText("E-mail"), "bia@example.com");
    await user.type(screen.getByLabelText("Quantidade pretendida"), "3");
    await user.type(screen.getByLabelText("Mensagem (opcional)"), "Aniversário");
    await user.click(screen.getByRole("button", { name: "Enviar solicitação" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("essa data já passou");
    expect(screen.getByLabelText("Nome")).toHaveValue("Bia");
    expect(screen.getByLabelText("E-mail")).toHaveValue("bia@example.com");
    expect(screen.getByLabelText("Quantidade pretendida")).toHaveDisplayValue("3");
    expect(screen.getByLabelText("Mensagem (opcional)")).toHaveValue("Aniversário");
    await user.click(screen.getByRole("button", { name: "Enviar solicitação" }));
    expect(await screen.findByText("Recebemos sua sugestão. Ainda não confirma a fornada.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Enviar solicitação" })).toBeEnabled();
    expect(screen.getByLabelText("Nome")).toHaveValue("Bia");
    expect(vi.mocked(submitDateRequest)).toHaveBeenCalledTimes(2);
  });
});

describe("parseIntendedQuantity", () => {
  it("só aceita inteiro a partir de 1", () => {
    expect(parseIntendedQuantity("")).toBeNull();
    expect(parseIntendedQuantity(" ")).toBeNull();
    expect(parseIntendedQuantity("0")).toBeNull();
    expect(parseIntendedQuantity("-1")).toBeNull();
    expect(parseIntendedQuantity("1.5")).toBeNull();
    expect(parseIntendedQuantity("1")).toBe(1);
    expect(parseIntendedQuantity("12")).toBe(12);
  });
});
