import { ChevronsUpDown } from "lucide-react";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

export function WorkspaceSelector() {
  return (
    <DropdownMenu>
      <DropdownMenuTrigger className="flex items-center gap-2 rounded-md border border-border px-2.5 py-1.5 text-sm font-medium outline-none transition-colors hover:bg-secondary focus-visible:ring-2 focus-visible:ring-ring">
        Default Workspace
        <ChevronsUpDown className="h-3.5 w-3.5 text-muted-foreground" />
      </DropdownMenuTrigger>
      <DropdownMenuContent align="start" className="w-56">
        <DropdownMenuItem disabled>Default Workspace</DropdownMenuItem>
        <DropdownMenuItem disabled className="text-muted-foreground">
          Multi-workspace support coming soon
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
