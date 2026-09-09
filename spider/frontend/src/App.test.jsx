import { describe, it, expect, afterEach, vi, beforeEach } from "vitest";
import { render, screen, cleanup, act } from "@testing-library/react";
import App from "./App.jsx";
import { resolveSurface } from "./surfaces.js";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

beforeEach(() => {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ items: [], productVersion: "0.20.0", status: "UP" }),
    }),
  );
});

describe("surface routing", () => {
  it("maps the commercial hub, SpiderBank satellite and Console separately", () => {
    expect(resolveSurface("/")).toBe("hub");
    expect(resolveSurface("/demo/contextual-link")).toBe("hub");
    expect(resolveSurface("/spiderbank")).toBe("spiderbank");
    expect(resolveSurface("/spiderbank/")).toBe("spiderbank");
    expect(resolveSurface("/spiderbank/entry")).toBe("spiderbank");
    expect(resolveSurface("/console")).toBe("console");
    expect(resolveSurface("/console/")).toBe("console");
  });

  it("opens the Experience Hub at the application root", () => {
    window.history.pushState({}, "", "/");
    render(<App />);
    expect(screen.getByTestId("experience-hub")).toBeInTheDocument();
    expect(screen.getByTestId("hub-brand")).toHaveTextContent("Plataforma Contextual");
    expect(screen.getByTestId("hub-headline")).toHaveTextContent(/caminhos executáveis/i);
    expect(screen.queryByTestId("spiderbank-entry")).not.toBeInTheDocument();
    expect(screen.queryByTestId("spider-console")).not.toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Home operacional" })).not.toBeInTheDocument();
  });

  it("opens SpiderBank at /spiderbank without inventing partner context", () => {
    window.history.pushState({}, "", "/spiderbank");
    render(<App />);
    expect(screen.getByTestId("spiderbank-entry")).toBeInTheDocument();
    expect(screen.getByTestId("direct-entry")).toBeInTheDocument();
    expect(screen.queryByTestId("open-provenance")).not.toBeInTheDocument();
    expect(screen.queryByTestId("experience-hub")).not.toBeInTheDocument();
  });

  it("opens Spider Console at /console", async () => {
    window.history.pushState({}, "", "/console");
    render(<App />);
    expect(await screen.findByTestId("spider-console")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Home operacional" })).toBeInTheDocument();
    expect(screen.queryByTestId("spiderbank-entry")).not.toBeInTheDocument();
    expect(screen.queryByTestId("experience-hub")).not.toBeInTheDocument();
  });

  it("keeps the legacy demonstration route on the Experience Hub", () => {
    window.history.pushState({}, "", "/demo/contextual-link");
    render(<App />);
    expect(screen.getByTestId("experience-hub")).toBeInTheDocument();
    expect(screen.getByTestId("open-partner")).toHaveAttribute(
      "href",
      "http://127.0.0.1:8080/demo/partner/agro-hoje",
    );
  });

  it("follows browser history between surfaces", async () => {
    window.history.pushState({}, "", "/");
    render(<App />);
    expect(screen.getByTestId("experience-hub")).toBeInTheDocument();
    await act(async () => {
      window.history.pushState({}, "", "/console");
      window.dispatchEvent(new PopStateEvent("popstate"));
    });
    expect(await screen.findByTestId("spider-console")).toBeInTheDocument();
    await act(async () => {
      window.history.pushState({}, "", "/spiderbank");
      window.dispatchEvent(new PopStateEvent("popstate"));
    });
    expect(screen.getByTestId("spiderbank-entry")).toBeInTheDocument();
    await act(async () => {
      window.history.pushState({}, "", "/");
      window.dispatchEvent(new PopStateEvent("popstate"));
    });
    expect(screen.getByTestId("experience-hub")).toBeInTheDocument();
  });
});
