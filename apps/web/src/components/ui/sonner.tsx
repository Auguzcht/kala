import {
  CircleCheckIcon,
  InfoIcon,
  OctagonXIcon,
  TriangleAlertIcon,
} from "lucide-react"
import { useTheme } from "next-themes"
import { Toaster as Sonner, type ToasterProps } from "sonner"
import { cn } from "@/lib/utils"
import { Spinner } from "@/components/ui/spinner"

const Toaster = ({ className, ...props }: ToasterProps) => {
  const { forcedTheme, resolvedTheme } = useTheme()

  return (
    <Sonner
      theme={(forcedTheme ?? resolvedTheme ?? "light") as ToasterProps["theme"]}
      className={cn("toaster group [&_[data-description]]:text-muted-foreground!", className)}
      icons={{
        success: <CircleCheckIcon className="size-4" />,
        info: <InfoIcon className="size-4" />,
        warning: <TriangleAlertIcon className="size-4" />,
        error: <OctagonXIcon className="size-4" />,
        loading: <Spinner aria-hidden />,
      }}
      style={
        {
          "--normal-bg": "var(--popover)",
          "--normal-text": "var(--popover-foreground)",
          "--normal-border": "var(--border)",
          "--border-radius": "var(--radius)",
        } as React.CSSProperties
      }
      {...props}
    />
  )
}

export { Toaster }
