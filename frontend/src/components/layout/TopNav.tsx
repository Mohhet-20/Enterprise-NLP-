import { Breadcrumbs } from "@/components/layout/Breadcrumbs";
import { GlobalSearchTrigger } from "@/components/layout/CommandPalette";
import { SystemStatus } from "@/components/layout/SystemStatus";
import { NotificationCenter } from "@/components/layout/NotificationCenter";
import { ThemeToggle } from "@/components/layout/ThemeToggle";
import { WorkspaceSelector } from "@/components/layout/WorkspaceSelector";
import { UserMenu } from "@/components/layout/UserMenu";

export function TopNav() {
  return (
    <header className="flex h-14 items-center justify-between gap-4 border-b border-border bg-background px-4">
      <div className="flex items-center gap-4">
        <WorkspaceSelector />
        <Breadcrumbs />
      </div>

      <div className="flex flex-1 items-center justify-end gap-2">
        <GlobalSearchTrigger />
        <SystemStatus />
        <NotificationCenter />
        <ThemeToggle />
        <UserMenu />
      </div>
    </header>
  );
}
