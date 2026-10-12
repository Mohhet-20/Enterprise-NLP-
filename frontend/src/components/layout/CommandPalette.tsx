import { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { LayoutDashboard, LogOut, Sun } from "lucide-react";
import {
  CommandDialog,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from "@/components/ui/command";
import { useUIStore } from "@/stores/useUIStore";
import { useThemeStore } from "@/stores/useThemeStore";
import { useLogout } from "@/hooks/useLogout";
import { navItems } from "@/components/layout/nav-config";

export function CommandPalette() {
  const open = useUIStore((s) => s.commandPaletteOpen);
  const setOpen = useUIStore((s) => s.setCommandPaletteOpen);
  const toggleTheme = useThemeStore((s) => s.toggleTheme);
  const logout = useLogout();
  const navigate = useNavigate();

  useEffect(() => {
    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "k" && (event.metaKey || event.ctrlKey)) {
        event.preventDefault();
        setOpen(!open);
      }
    }
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [open, setOpen]);

  function runAndClose(action: () => void) {
    action();
    setOpen(false);
  }

  return (
    <CommandDialog open={open} onOpenChange={setOpen}>
      <CommandInput placeholder="Search pages and actions…" />
      <CommandList>
        <CommandEmpty>No results found.</CommandEmpty>
        <CommandGroup heading="Navigate">
          {navItems
            .filter((item) => item.implemented)
            .map((item) => (
              <CommandItem key={item.path} onSelect={() => runAndClose(() => navigate(item.path))}>
                <item.icon className="h-4 w-4" />
                {item.label}
              </CommandItem>
            ))}
        </CommandGroup>
        <CommandGroup heading="Actions">
          <CommandItem onSelect={() => runAndClose(toggleTheme)}>
            <Sun className="h-4 w-4" />
            Toggle theme
          </CommandItem>
          <CommandItem
            onSelect={() =>
              runAndClose(() => {
                logout.mutate();
                navigate("/login");
              })
            }
          >
            <LogOut className="h-4 w-4" />
            Log out
          </CommandItem>
        </CommandGroup>
      </CommandList>
    </CommandDialog>
  );
}

export function GlobalSearchTrigger() {
  const setOpen = useUIStore((s) => s.setCommandPaletteOpen);
  return (
    <button
      onClick={() => setOpen(true)}
      className="flex w-64 items-center gap-2 rounded-md border border-border bg-background px-3 py-1.5 text-sm text-muted-foreground transition-colors hover:bg-secondary"
    >
      <LayoutDashboard className="h-3.5 w-3.5" />
      <span className="flex-1 text-left">Search…</span>
      <kbd className="rounded border border-border bg-muted px-1.5 py-0.5 font-mono text-[10px]">⌘K</kbd>
    </button>
  );
}
