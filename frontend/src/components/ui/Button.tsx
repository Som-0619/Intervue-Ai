import * as React from "react"

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'default' | 'outline' | 'secondary' | 'ghost' | 'destructive'
  size?: 'default' | 'sm' | 'lg' | 'icon'
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className = "", variant = "default", size = "default", ...props }, ref) => {
    const baseStyle = "inline-flex items-center justify-center font-medium rounded-xl text-sm transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-zinc-900 focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 active:scale-[0.99]"
    
    const variants = {
      default: "bg-zinc-900 text-white hover:bg-zinc-800 shadow-sm",
      outline: "border border-zinc-200 bg-white hover:bg-zinc-50 text-zinc-900 shadow-sm",
      secondary: "bg-zinc-100 text-zinc-900 hover:bg-zinc-200",
      ghost: "hover:bg-zinc-100 text-zinc-700 hover:text-zinc-900",
      destructive: "bg-red-600 text-white hover:bg-red-700 shadow-sm"
    }

    const sizes = {
      default: "h-10 px-4 py-2",
      sm: "h-8 px-3 text-xs rounded-lg",
      lg: "h-12 px-6 text-base rounded-xl",
      icon: "h-10 w-10 p-0"
    }

    return (
      <button
        ref={ref}
        className={`${baseStyle} ${variants[variant]} ${sizes[size]} ${className}`}
        {...props}
      />
    )
  }
)
Button.displayName = "Button"
