import * as React from "react"

export function Skeleton({ className = "", ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div className={`animate-pulse rounded-lg bg-zinc-200/80 ${className}`} {...props} />
  )
}
