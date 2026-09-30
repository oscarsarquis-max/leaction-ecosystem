import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { BakeCalendar } from "./BakeCalendar";
import { previewCalendar } from "./calendarApi";
import { fetchOperations } from "./operationsApi";

vi.mock("./operationsApi", () => ({
  fetchOperations: vi.fn(async () => ({
    preview_protection: false,
    orders_enabled: true,
    payments_enabled: true,
    date_requests_enabled: true,
    house_fidelity_active: true,
    business_date: "2026-09-29",
    message: null,
  })),
}));

vi.mock("./calendarApi", () => ({
  previewCalendar: vi.fn(async () => ({
    occupancy_enabled: false,
    reservation_policy: "unset",
    timezone: "America/Sao_Paulo",
    selected_date: null,
    selected_status: null,
    full_message: null,
    alternatives: [],
    notice: "As datas com o pão mostram fornadas abertas.",
    days: [
      {
        date: "2026-09-23",
        status: "available",
        origin: "default",
        daily_physical_limit: 8,
        daily_base_limit: 4,
        committed_physical: 0,
        remaining_physical: 8,
        reason: "none",
        accessible_label: "Quarta-feira, 23 de setembro: fornada disponível",
        weekday_name: "quarta",
        eligible: true,
        windows: [],
      },
    ],
  })),
}));

describe("BakeCalendar", () => {
  it("mostra o calendário na vitrine com legenda e dia disponível", async () => {
    render(<BakeCalendar lines={[]} layout="shelf" />);
    expect(await screen.findByRole("heading", { name: "Escolha sua fornada" })).toBeInTheDocument();
    expect(screen.queryByText("Agenda de A Loja")).not.toBeInTheDocument();
    expect(screen.queryByText(/As datas com o pão/)).not.toBeInTheDocument();
    expect(screen.getByText("Dia de produção aberto")).toBeInTheDocument();
    expect(screen.getByText("Precisa de outra data?")).toBeInTheDocument();
    expect(screen.queryByText("Fornada disponível")).not.toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Quarta-feira, 23 de setembro: fornada disponível" }),
    ).toBeInTheDocument();
    expect(screen.queryByText("Fornada no limite")).not.toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Quarta-feira, 23 de setembro: fornada disponível" }).querySelector("svg"),
    ).not.toBeNull();
  });

  it("mostra o ícone de pão em dia de produção mesmo quando a ficha ainda não é elegível", async () => {
    vi.mocked(previewCalendar).mockResolvedValueOnce({
      occupancy_enabled: true,
      reservation_policy: "admin_accept",
      timezone: "America/Sao_Paulo",
      selected_date: null,
      selected_status: null,
      full_message: null,
      alternatives: [],
      notice: null,
      days: [
        {
          date: "2026-09-30",
          status: "not_eligible",
          origin: "default",
          daily_physical_limit: 15,
          daily_base_limit: 5,
          committed_physical: 0,
          remaining_physical: 15,
          reason: "unknown_units",
          accessible_label: "quarta-feira, 30 de setembro: indisponível para esta seleção",
          weekday_name: "quarta",
          eligible: false,
          at_capacity: false,
          windows: [],
        },
      ],
    });
    render(<BakeCalendar lines={[{ kind: "product", variant_id: "v1", quantity: 1 }]} />);
    const day = await screen.findByRole("button", {
      name: "quarta-feira, 30 de setembro: indisponível para esta seleção",
    });
    expect(day).toBeEnabled();
    expect(day.querySelector("svg")).not.toBeNull();
    expect(screen.getByText("Dia de produção aberto")).toBeInTheDocument();
    expect(screen.getByText("Escolha um dia com o ícone de pão.")).toBeInTheDocument();
  });

  it("não deixa escolher fornada completa e esconde instrução sem vaga", async () => {
    vi.mocked(previewCalendar).mockResolvedValueOnce({
      occupancy_enabled: true,
      reservation_policy: "admin_accept",
      timezone: "America/Sao_Paulo",
      selected_date: null,
      selected_status: null,
      full_message: "Essa fornada já está completa.",
      alternatives: [],
      notice: null,
      days: [
        {
          date: "2026-09-30",
          status: "full",
          origin: "default",
          daily_physical_limit: 15,
          daily_base_limit: 5,
          committed_physical: 15,
          remaining_physical: 0,
          reason: "physical",
          accessible_label: "quarta-feira, 30 de setembro: fornada completa",
          weekday_name: "quarta",
          eligible: false,
          at_capacity: true,
          windows: [],
        },
      ],
    });
    render(<BakeCalendar lines={[]} />);
    const day = await screen.findByRole("button", {
      name: "quarta-feira, 30 de setembro: fornada completa",
    });
    expect(day).toBeDisabled();
    expect(day.querySelector("svg")).not.toBeNull();
    expect(screen.getByText("Fornada completa")).toBeInTheDocument();
    expect(screen.getByText("Fornada no limite")).toBeInTheDocument();
    expect(screen.queryByText("Escolha um dia com o ícone de pão.")).not.toBeInTheDocument();
  });

  it("não deixa encomendar o dia de hoje e abre a sugestão no bloco verde", async () => {
    vi.mocked(previewCalendar).mockResolvedValueOnce({
      occupancy_enabled: true,
      reservation_policy: "admin_accept",
      timezone: "America/Sao_Paulo",
      business_date: "2026-09-29",
      selected_date: null,
      selected_status: null,
      full_message: null,
      alternatives: [],
      notice: null,
      days: [
        {
          date: "2026-09-29",
          status: "same_day",
          origin: "default",
          daily_physical_limit: 15,
          daily_base_limit: 5,
          committed_physical: 0,
          remaining_physical: 15,
          reason: "same_day",
          accessible_label: "terça-feira, 29 de setembro: Pedidos pelo calendário são para os próximos dias",
          weekday_name: "terça",
          eligible: false,
          at_capacity: false,
          windows: [],
        },
      ],
    });
    render(<BakeCalendar lines={[]} layout="shelf" />);
    const today = await screen.findByRole("button", {
      name: "terça-feira, 29 de setembro: Pedidos pelo calendário são para os próximos dias",
    });
    expect(today).toBeDisabled();
    expect(today.querySelector("svg")).not.toBeNull();
    expect(screen.getByText("Precisa de outra data?")).toBeInTheDocument();
    await userEvent.setup().click(screen.getByRole("button", { name: "Sugerir uma data" }));
    expect(screen.getByLabelText("Data desejada")).toBeInTheDocument();
    expect(vi.mocked(fetchOperations)).toHaveBeenCalled();
  });

  it("não marca pão durante o erro de consulta", async () => {
    vi.mocked(previewCalendar).mockRejectedValueOnce(new Error("rede"));
    render(<BakeCalendar lines={[]} />);
    expect(await screen.findByText("Não foi possível consultar as fornadas agora.")).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Quarta-feira, 23 de setembro: fornada disponível" }),
    ).not.toBeInTheDocument();
  });
});
