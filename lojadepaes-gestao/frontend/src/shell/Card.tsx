import type { ReactNode } from "react";

type Props = {
  children: ReactNode;
  className?: string;
};

export function Card({ children, className }: Props) {
  return <div className={["gestao-card", className].filter(Boolean).join(" ")}>{children}</div>;
}
