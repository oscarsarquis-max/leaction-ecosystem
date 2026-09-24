import { render, screen } from "@testing-library/react";
import { BakeCalendar } from "./BakeCalendar";
import { previewCalendar } from "./calendarApi";

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
    expect(screen.queryByText("Agenda da padaria")).not.toBeInTheDocument();
    expect(screen.getByText(/As datas com o pão/)).toBeInTheDocument();
    expect(screen.getByText("Dia de produção aberto")).toBeInTheDocument();
    expect(screen.queryByText("Fornada disponível")).not.toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Quarta-feira, 23 de setembro: fornada disponível" }),
    ).toBeInTheDocument();
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
