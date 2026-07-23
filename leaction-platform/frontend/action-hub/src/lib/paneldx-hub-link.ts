/**
 * Vínculo público PanelDX ↔ Action Hub.
 * Mantém false enquanto o PanelDX público estiver desativado / substituído pelo mudaedu.
 * Não reative sem pedido explícito.
 */
export const PANEL_DX_HUB_LINKED = false;

export function isPanelDxHubLinked(): boolean {
  return PANEL_DX_HUB_LINKED;
}
