/**
 * Debounce simples (sem lodash) — cancela e reagenda a execução.
 * Guarda os últimos argumentos para flush() no unmount / pagehide.
 * @param {(...args: any[]) => any} fn
 * @param {number} wait ms
 */
export function debounce(fn, wait = 700) {
  let timer = null
  let lastArgs = null

  function debounced(...args) {
    lastArgs = args
    if (timer) clearTimeout(timer)
    timer = setTimeout(() => {
      timer = null
      const queued = lastArgs
      lastArgs = null
      if (queued) fn(...queued)
    }, wait)
  }

  debounced.cancel = () => {
    if (timer) clearTimeout(timer)
    timer = null
    lastArgs = null
  }

  debounced.flush = (...args) => {
    if (timer) clearTimeout(timer)
    timer = null
    const queued = args.length ? args : lastArgs
    lastArgs = null
    if (!queued) return undefined
    return fn(...queued)
  }

  debounced.pending = () => timer != null || lastArgs != null

  return debounced
}
