import { useCallback, useEffect, useState } from "react";

type Availability = "consulting" | "available" | "unavailable";

type SystemInfo = {
  name: string;
  stage: string;
  financialOperationsAvailable: boolean;
  spiderIntegrationStatus: string;
};

export function FoundationPage() {
  const [availability, setAvailability] = useState<Availability>("consulting");
  const [info, setInfo] = useState<SystemInfo | null>(null);
  const [message, setMessage] = useState("Consultando a API local.");

  const verify = useCallback(async () => {
    setAvailability("consulting");
    setMessage("Consultando a API local.");
    try {
      const response = await fetch("/api/v1/system/info", { headers: { Accept: "application/json" } });
      if (!response.ok) {
        throw new Error("unavailable");
      }
      const body = (await response.json()) as SystemInfo;
      setInfo(body);
      setAvailability("available");
      setMessage("API local disponível.");
    } catch {
      setInfo(null);
      setAvailability("unavailable");
      setMessage("API local indisponível. Tente verificar novamente.");
    }
  }, []);

  useEffect(() => {
    void verify();
  }, [verify]);

  return (
    <main className="page">
      <header className="brand">
        <p className="brand__name">ActionFinance</p>
        <p className="brand__env">Ambiente local de desenvolvimento</p>
      </header>
      <section className="panel" aria-labelledby="foundation-title">
        <h1 id="foundation-title">Fundação técnica. Operações financeiras ainda não disponíveis.</h1>
        <p className={`status status--${availability}`} role="status">
          <span className="status__icon" aria-hidden="true">
            {availability === "consulting" ? "…" : availability === "available" ? "✓" : "!"}
          </span>
          <span>{message}</span>
        </p>
        <p>Integração Spider: ainda não implementada.</p>
        {info ? <p>Etapa: {info.stage}. Operações financeiras: não disponíveis.</p> : null}
        <button type="button" onClick={() => void verify()}>
          Verificar novamente
        </button>
      </section>
    </main>
  );
}
