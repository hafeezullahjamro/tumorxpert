import { type ButtonHTMLAttributes } from "react";
import { Slot } from "@radix-ui/react-slot";
import { clsx } from "clsx";

const baseStyles =
  "inline-flex items-center justify-center rounded-xl border border-transparent px-4 py-2.5 text-sm font-semibold transition duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-offset-transparent disabled:cursor-not-allowed disabled:opacity-60";

const variants = {
  primary:
    "bg-primary text-primary-foreground shadow-sm hover:-translate-y-0.5 hover:bg-[#0d4352] hover:shadow-md focus-visible:ring-primary",
  secondary:
    "border-slate-300 bg-white text-slate-900 hover:-translate-y-0.5 hover:bg-slate-50 hover:shadow-sm focus-visible:ring-secondary",
  ghost: "bg-transparent text-primary hover:bg-accent/70 focus-visible:ring-muted"
} as const;

type ButtonVariant = keyof typeof variants;

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  asChild?: boolean;
}

export function Button({ className, variant = "primary", asChild = false, ...props }: ButtonProps) {
  const Component = asChild ? Slot : "button";
  return <Component className={clsx(baseStyles, variants[variant], className)} {...props} />;
}
