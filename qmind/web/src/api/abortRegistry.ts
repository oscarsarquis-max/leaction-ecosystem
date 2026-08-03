/**
 * Tracks in-flight AbortControllers so tenant switch / logout can cancel them.
 */

const controllers = new Set<AbortController>();

export function trackAbortController(controller: AbortController): () => void {
  controllers.add(controller);
  return () => {
    controllers.delete(controller);
  };
}

export function abortAllInFlight(reason = "tenant_switch"): void {
  for (const c of controllers) {
    try {
      c.abort(reason);
    } catch {
      // ignore
    }
  }
  controllers.clear();
}

export function createTrackedAbortController(): AbortController {
  const c = new AbortController();
  const release = trackAbortController(c);
  c.signal.addEventListener("abort", release, { once: true });
  return c;
}
