import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { PartnerPhoto } from "./PartnerPhoto";

describe("PartnerPhoto", () => {
  it("mostra a foto e troca pelo fundo neutro se ela não carregar", () => {
    const { container } = render(<PartnerPhoto className="mkp-card-photo" src="/api/v1/marketplace/media/x" alt="Queijo" lazy />);
    const photo = screen.getByRole("img", { name: "Queijo" });
    expect(photo).toHaveAttribute("loading", "lazy");
    fireEvent.error(photo);
    expect(screen.queryByRole("img")).not.toBeInTheDocument();
    expect(container.querySelector(".mkp-photo-empty")).not.toBeNull();
  });

  it("sem foto mostra o fundo neutro", () => {
    const { container } = render(<PartnerPhoto className="mkp-hero-photo" src="" alt="Foto" />);
    expect(screen.queryByRole("img")).not.toBeInTheDocument();
    expect(container.querySelector(".mkp-hero-photo.mkp-photo-empty")).not.toBeNull();
  });
});
