import { forwardRef, type ButtonHTMLAttributes, type ReactNode } from "react";

type Variant = "primary" | "secondary" | "danger";

type Props = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: Variant;
  children: ReactNode;
};

export const Button = forwardRef<HTMLButtonElement, Props>(function Button(
  { variant = "secondary", className, type = "button", children, ...rest },
  ref,
) {
  const tone = variant === "primary" ? "is-primary" : variant === "danger" ? "is-danger" : "";
  return (
    <button ref={ref} type={type} className={["admin-btn", tone, className].filter(Boolean).join(" ")} {...rest}>
      {children}
    </button>
  );
});
