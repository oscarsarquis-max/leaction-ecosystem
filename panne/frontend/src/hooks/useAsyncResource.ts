import { useEffect, useRef, useState, type DependencyList } from "react";
import { isCancelledError } from "../api/errors";

export type ResourceState<T> =
  | { kind: "carregando" }
  | { kind: "ok"; data: T }
  | { kind: "erro"; error: unknown };

type Options = {
  /** Quando false, limpa dados sensíveis e não dispara carga. */
  enabled?: boolean;
};

/**
 * Carga assíncrona com geração + montagem (R026-004 isolamento):
 * - mudança de deps entra imediatamente em `carregando` (sem dados anteriores);
 * - erro anterior é limpo;
 * - geração anterior não atualiza a nova;
 * - cancelamento não é erro apresentável;
 * - `enabled=false` não conserva dados da organização anterior.
 *
 * Inclua sempre `active?.organization_id` (ou equivalente) nas deps de recursos escopados.
 * Não dependa só da identidade do objeto `api`.
 */
export function useAsyncResource<T>(
  factory: () => Promise<T>,
  deps: DependencyList,
  enabledOrOptions: boolean | Options = true,
): {
  state: ResourceState<T>;
  reload: () => void;
  data: T | null;
  error: unknown;
  loading: boolean;
} {
  const enabled =
    typeof enabledOrOptions === "boolean" ? enabledOrOptions : (enabledOrOptions.enabled ?? true);
  const [state, setState] = useState<ResourceState<T>>({ kind: "carregando" });
  const generation = useRef(0);
  const mounted = useRef(true);
  const factoryRef = useRef(factory);
  factoryRef.current = factory;

  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
    };
  }, []);

  useEffect(() => {
    if (!enabled) {
      generation.current += 1;
      setState({ kind: "carregando" });
      return;
    }

    const token = ++generation.current;
    // Limpa imediatamente conteúdo/erro da geração anterior (troca de org/rota).
    setState({ kind: "carregando" });

    let abandoned = false;
    void factoryRef
      .current()
      .then((data) => {
        if (!mounted.current || abandoned || generation.current !== token) return;
        setState({ kind: "ok", data });
      })
      .catch((error) => {
        if (!mounted.current || abandoned || generation.current !== token) return;
        if (isCancelledError(error)) {
          // Mantém carregando só se ainda for a geração atual; a próxima carga (nova
          // geração) ou o cleanup abandonará este token. Evita flash de erro.
          return;
        }
        setState({ kind: "erro", error });
      });

    return () => {
      abandoned = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, enabled]);

  const reload = () => {
    if (!enabled) return;
    const token = ++generation.current;
    setState({ kind: "carregando" });
    void factoryRef
      .current()
      .then((data) => {
        if (!mounted.current || generation.current !== token) return;
        setState({ kind: "ok", data });
      })
      .catch((error) => {
        if (!mounted.current || generation.current !== token) return;
        if (isCancelledError(error)) return;
        setState({ kind: "erro", error });
      });
  };

  return {
    state,
    reload,
    data: state.kind === "ok" ? state.data : null,
    error: state.kind === "erro" ? state.error : null,
    loading: state.kind === "carregando",
  };
}
