import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { LoadingState } from "../components/Feedback";

export function CallbackPage() {
  const { completeCallback } = useAuth();
  const navigate = useNavigate();
  const [erro, setErro] = useState<string | null>(null);

  useEffect(() => {
    let ativo = true;
    completeCallback()
      .then(() => {
        if (ativo) navigate("/", { replace: true });
      })
      .catch((error: unknown) => {
        if (ativo) {
          setErro(error instanceof Error ? error.message : "Falha no retorno de autenticação.");
        }
      });
    return () => {
      ativo = false;
    };
  }, [completeCallback, navigate]);

  if (erro) {
    return (
      <main className="feedback" role="alert">
        <h1>Não foi possível concluir o acesso</h1>
        <p>{erro}</p>
      </main>
    );
  }
  return <LoadingState>Concluindo autenticação…</LoadingState>;
}
