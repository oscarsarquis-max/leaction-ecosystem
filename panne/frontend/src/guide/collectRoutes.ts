import { isValidElement, type ReactElement, type ReactNode } from "react";
import { AppRoutes } from "../App";

function walk(node: ReactNode, acc: string[]): void {
  if (node == null || typeof node === "boolean") return;
  if (Array.isArray(node)) {
    node.forEach((item) => walk(item, acc));
    return;
  }
  if (!isValidElement(node)) return;
  const element = node as ReactElement<{ path?: string; children?: ReactNode }>;
  if (typeof element.props.path === "string" && element.props.path !== "/") {
    acc.push(element.props.path);
  }
  walk(element.props.children, acc);
}

export function collectRouterPaths(): string[] {
  const paths: string[] = [];
  walk(AppRoutes(), paths);
  return [...new Set(paths)];
}
