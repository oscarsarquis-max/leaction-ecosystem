import { describe, expect, it } from "vitest";
import { safeAdminNext, storefrontAccessUrl } from "./safePath";

describe("destino interno após login", () => {
  it("aceita rotas administrativas conhecidas e rejeita o restante", () => {
    expect(safeAdminNext(null)).toBe("/admin/produtos");
    expect(safeAdminNext("/admin/produtos")).toBe("/admin/produtos");
    expect(safeAdminNext("/admin/produtos/novo")).toBe("/admin/produtos/novo");
    expect(safeAdminNext("/admin/pedidos")).toBe("/admin/pedidos");
    expect(safeAdminNext("/admin/pedidos/abc")).toBe("/admin/pedidos/abc");
    expect(safeAdminNext("/admin/login")).toBe("/admin/produtos");
    expect(safeAdminNext("/admin")).toBe("/admin/produtos");
    expect(safeAdminNext("https://evil.example/admin/produtos")).toBe("/admin/produtos");
    expect(safeAdminNext("//evil.example")).toBe("/admin/produtos");
    expect(safeAdminNext("/paes/x")).toBe("/admin/produtos");
    expect(safeAdminNext("/admin/../etc")).toBe("/admin/produtos");
    expect(storefrontAccessUrl("/admin/pedidos")).toBe("/?next=%2Fadmin%2Fpedidos#acesso");
  });
});
