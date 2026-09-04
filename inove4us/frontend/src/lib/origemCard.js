export const ORIGEM_CARD_CATALOGO = 'catalogo'
export const ORIGEM_CARD_CUSTOM = 'custom'

export function carimbarCustom(task) {
  return {
    ...task,
    origem_card: ORIGEM_CARD_CUSTOM,
    editado: Boolean(task?.editado),
  }
}

export function marcarEditado(task) {
  return { ...task, editado: true }
}
