import { useRef, useState } from "react";
import { ApiError } from "../api/errors";

type Runner<T> = (idempotencyKey: string) => Promise<T>;

export function useCommand() {
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<ApiError | Error | null>(null);
  const keyRef = useRef<{ fingerprint: string; key: string } | null>(null);
  const pendingRef = useRef(false);

  async function run<T>(fingerprint: string, action: Runner<T>): Promise<T | null> {
    if (pendingRef.current) return null;
    const reused = keyRef.current?.fingerprint === fingerprint ? keyRef.current.key : crypto.randomUUID();
    keyRef.current = { fingerprint, key: reused };
    pendingRef.current = true;
    setPending(true);
    try {
      const result = await action(reused);
      keyRef.current = null;
      setError(null);
      return result;
    } catch (err) {
      const next = err instanceof Error ? err : new Error("Falha no comando.");
      setError(next);
      throw next;
    } finally {
      pendingRef.current = false;
      setPending(false);
    }
  }

  return { pending, error, run, clearError: () => setError(null) };
}
