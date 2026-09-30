import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Modal } from "./Modal";

describe("Modal", () => {
  it("portals the dialog outside a parent form", async () => {
    const user = userEvent.setup();
    const onClose = vi.fn();
    render(
      <form className="form">
        <input defaultValue="parent" aria-label="Campo pai" />
        <Modal title="Diálogo portado" onClose={onClose}>
          <button type="button">Primeiro foco</button>
        </Modal>
      </form>,
    );
    const dialog = await screen.findByRole("dialog");
    expect(dialog.parentElement).toBe(document.body);
    expect(document.querySelector("form.form dialog")).toBeNull();
    expect(screen.getByRole("button", { name: "Primeiro foco" })).toHaveFocus();
    await user.keyboard("{Escape}");
    expect(onClose).toHaveBeenCalled();
  });
});
