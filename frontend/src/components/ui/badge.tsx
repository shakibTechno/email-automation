import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"

import { cn } from "@/lib/utils"

const badgeVariants = cva(
  "inline-flex items-center gap-1.5 rounded-[5px] border px-2 py-0.5 font-mono text-[10px] font-medium uppercase tracking-wider transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2",
  {
    variants: {
      variant: {
        default:
          "border-transparent bg-brand/[.14] text-brand",
        secondary:
          "border-transparent bg-secondary text-muted-foreground",
        destructive:
          "border-transparent bg-destructive/[.14] text-destructive",
        success: "border-transparent bg-success/[.14] text-success",
        warning: "border-transparent bg-warning/[.14] text-warning",
        info: "border-transparent bg-info/[.14] text-info",
        outline: "border-border text-muted-foreground",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  }
)

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return (
    <div className={cn(badgeVariants({ variant }), className)} {...props} />
  )
}

export { Badge, badgeVariants }
