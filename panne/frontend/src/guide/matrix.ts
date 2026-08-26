import { collectRouterPaths } from "./collectRoutes";
import { matchGuide, resolveGuide } from "./routes";

export type RouteMatrixRow = {
  route: string;
  page: string;
  role: string;
  avatar: string;
  guide: string;
  entity: string;
  next: string;
};

export function samplePath(path: string): string {
  return path.replace(/:([A-Za-z]+)/g, "amostra");
}

export function buildAssistantMatrix(): RouteMatrixRow[] {
  return collectRouterPaths()
    .filter((path) => path !== "/")
    .map((path) => {
      const sample = samplePath(path);
      const { guide, specific } = resolveGuide(sample);
      return {
        route: path,
        page: guide.title,
        role: "perfil demo vigente",
        avatar: "sim — shell autenticado ou login público",
        guide: specific ? "específico" : "fallback",
        entity: guide.entity,
        next: guide.next,
      };
    });
}

export function guideGaps(): string[] {
  return collectRouterPaths().filter((path) => path !== "/" && !matchGuide(samplePath(path)));
}
