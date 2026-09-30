export function stepsToMethodText(steps: string[]): string {
  return steps.map((item) => item.replace(/\r\n/g, "\n").trim()).filter(Boolean).join("\n\n");
}

export function methodTextToSteps(value: string): string[] {
  const cleaned = value.replace(/\r\n/g, "\n").trim();
  if (!cleaned) {
    return [];
  }
  return cleaned
    .split(/\n\s*\n/)
    .map((item) => item.trim())
    .filter(Boolean);
}

export function ingredientsToText(items: string[]): string {
  return items.join("\n");
}

export function textToIngredients(value: string): string[] {
  return value
    .replace(/\r\n/g, "\n")
    .split("\n")
    .map((item) => item.trim())
    .filter(Boolean);
}
