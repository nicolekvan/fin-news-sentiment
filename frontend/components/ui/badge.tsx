import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center gap-1 whitespace-nowrap rounded border px-1.5 py-0.5 text-[11px] font-medium leading-none",
  {
    variants: {
      variant: {
        default: "border-border bg-panel-2 text-text",
        outline: "border-border text-muted",
        bull: "border-bull/40 bg-bull/10 text-bull",
        bear: "border-bear/40 bg-bear/10 text-bear",
        neutral: "border-neutral/40 bg-neutral/10 text-neutral",
        unclear: "border-unclear/40 bg-unclear/10 text-unclear",
        accent: "border-accent/40 bg-accent/10 text-accent",
      },
    },
    defaultVariants: { variant: "default" },
  },
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLSpanElement>,
    VariantProps<typeof badgeVariants> {}

export function Badge({ className, variant, ...props }: BadgeProps) {
  return <span className={cn(badgeVariants({ variant }), className)} {...props} />;
}
