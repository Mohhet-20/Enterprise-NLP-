import { NavLink } from "react-router-dom";
import { motion } from "framer-motion";
import { ChevronsLeft, ChevronsRight, Waves } from "lucide-react";
import { cn } from "@/lib/utils";
import { useUIStore } from "@/stores/useUIStore";
import { navItems } from "@/components/layout/nav-config";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { Badge } from "@/components/ui/badge";

export function Sidebar() {
  const collapsed = useUIStore((s) => s.sidebarCollapsed);
  const toggleSidebar = useUIStore((s) => s.toggleSidebar);

  return (
    <aside
      className={cn(
        "flex h-screen flex-col border-r border-border bg-card transition-[width] duration-200",
        collapsed ? "w-[68px]" : "w-60"
      )}
    >
      <div className="flex h-14 items-center gap-2 border-b border-border px-4">
        <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-md bg-primary text-primary-foreground">
          <Waves className="h-4 w-4" />
        </div>
        {!collapsed && (
          <span className="font-display text-sm font-semibold tracking-tight">NLP Platform</span>
        )}
      </div>

      <nav className="flex-1 space-y-0.5 overflow-y-auto p-2">
        {navItems.map((item) => {
          const Icon = item.icon;
          const linkContent = (
            <NavLink
              key={item.path}
              to={item.implemented ? item.path : "#"}
              onClick={(e) => {
                if (!item.implemented) e.preventDefault();
              }}
              className={({ isActive }) =>
                cn(
                  "group relative flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                  item.implemented
                    ? isActive
                      ? "text-foreground"
                      : "text-muted-foreground hover:bg-secondary hover:text-foreground"
                    : "cursor-not-allowed text-muted-foreground/50"
                )
              }
              end
            >
              {({ isActive }) => (
                <>
                  {isActive && item.implemented && (
                    <motion.span
                      layoutId="sidebar-active-pill"
                      className="absolute inset-0 rounded-md bg-secondary"
                      transition={{ type: "spring", stiffness: 400, damping: 32 }}
                    />
                  )}
                  <Icon className="relative z-10 h-4 w-4 shrink-0" />
                  {!collapsed && <span className="relative z-10 truncate">{item.label}</span>}
                  {!collapsed && !item.implemented && (
                    <Badge variant="outline" className="relative z-10 ml-auto px-1.5 py-0 text-[10px] font-normal">
                      soon
                    </Badge>
                  )}
                </>
              )}
            </NavLink>
          );

          return collapsed ? (
            <Tooltip key={item.path}>
              <TooltipTrigger asChild>{linkContent}</TooltipTrigger>
              <TooltipContent side="right">{item.description}</TooltipContent>
            </Tooltip>
          ) : (
            linkContent
          );
        })}
      </nav>

      <button
        onClick={toggleSidebar}
        className="flex h-12 items-center justify-center border-t border-border text-muted-foreground transition-colors hover:bg-secondary hover:text-foreground"
        aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
      >
        {collapsed ? <ChevronsRight className="h-4 w-4" /> : <ChevronsLeft className="h-4 w-4" />}
      </button>
    </aside>
  );
}
