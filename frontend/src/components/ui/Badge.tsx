import * as React from "react"

export interface BadgeProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: 'default' | 'outline' | 'secondary' | 'success' | 'warning'
}

export function Badge({ className = "", variant = "default", ...props }: BadgeProps) {
  const base = "inline-flex items-center rounded-md px-2.5 py-0.5 text-xs font-semibold font-mono tracking-tight transition-colors"
  const variants = {
    default: "bg-zinc-900 text-white",
    outline: "border border-zinc-300 text-zinc-700 bg-white",
    secondary: "bg-zinc-100 text-zinc-800 border border-zinc-200",
    success: "bg-emerald-50 text-emerald-700 border border-emerald-200",
    warning: "bg-amber-50 text-amber-700 border border-amber-200"
  }
  return <div className={`${base} ${variants[variant]} ${className}`} {...props} />
}

