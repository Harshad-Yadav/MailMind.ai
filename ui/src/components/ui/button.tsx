import * as React from "react";

import { cn } from "@/lib/utils";

const variants = {
  default: "bg-ink text-white hover:bg-slate-800",
  secondary: "bg-white text-ink hover:bg-slate-50 border border-slate-200",
  ember: "bg-ember text-white hover:bg-orange-600",
};

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: keyof typeof variants;
}

export function Button({ className, variant = "default", ...props }: ButtonProps) {
  return (
    <button
      className={cn(
        "inline-flex items-center justify-center rounded-full px-4 py-2 text-sm font-semibold transition duration-200 disabled:cursor-not-allowed disabled:opacity-60",
        variants[variant],
        className,
      )}
      {...props}
    />
  );
}
