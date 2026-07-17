/**
 * Debounce simples (sem lodash) — cancela e reagenda a execução.
 * @param {(...args: any[]) => any} fn
 * @param {number} wait ms
 */
export function debounce(fn, wait = 700) {
  let timer = null

  function debounced(...args) {
    if (timer) clearTimeout(timer)
    timer = setTimeout(() => {
      timer = null
      fn(...args)
    }, wait)
  }

  debounced.cancel = () => {
    if (timer) clearTimeout(timer)
    timer = null
  }

  debounced.flush = (...args) => {
    if (timer) clearTimeout(timer)
    timer = null
    return fn(...args)
  }

  return debounced
}
