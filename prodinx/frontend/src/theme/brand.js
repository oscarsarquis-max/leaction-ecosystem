export const BRAND_COLORS = {
  vermelho: "#A6193C",
  laranja: "#F68B1F",
  cinza: "#646464",
  verde: "#004B2C",
};

export const SCORE_META = 70;
export const SCORE_ALERTA = 85;

export function getScoreStatus(score) {
  if (score < SCORE_META) return "failure";
  if (score < SCORE_ALERTA) return "alert";
  return "success";
}

export function getStatusColor(status) {
  switch (status) {
    case "failure":
      return BRAND_COLORS.vermelho;
    case "alert":
      return BRAND_COLORS.laranja;
    default:
      return BRAND_COLORS.verde;
  }
}

export function getScoreColor(score) {
  return getStatusColor(getScoreStatus(score));
}
