import { AdminApiError } from "./api";

export function accessMessage(error: unknown): string {
  if (error instanceof AdminApiError) {
    if (error.status === 503) {
      return "Acesso indisponível no momento";
    }
    if (error.status === 403) {
      return "Acesso indisponível no momento";
    }
    if (error.status === 401) {
      return "Usuário ou senha inválidos";
    }
    if (error.status === 429) {
      return "Muitas tentativas. Aguarde um pouco";
    }
    if (error.status === 0) {
      return "Acesso indisponível no momento";
    }
  }
  return "Acesso indisponível no momento";
}
