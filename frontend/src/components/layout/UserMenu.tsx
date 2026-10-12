import { useNavigate } from "react-router-dom";
import { LogOut, ShieldCheck } from "lucide-react";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { useAuthStore } from "@/stores/useAuthStore";
import { useLogout } from "@/hooks/useLogout";

function initialsFor(username: string): string {
  return username.slice(0, 2).toUpperCase();
}

export function UserMenu() {
  const user = useAuthStore((s) => s.user);
  const logout = useLogout();
  const navigate = useNavigate();

  if (!user) return null;

  async function handleLogout() {
    await logout.mutateAsync();
    navigate("/login");
  }

  return (
    <DropdownMenu>
      <DropdownMenuTrigger className="flex items-center gap-2 rounded-md p-1 outline-none transition-colors hover:bg-secondary focus-visible:ring-2 focus-visible:ring-ring">
        <Avatar>
          <AvatarFallback>{initialsFor(user.username)}</AvatarFallback>
        </Avatar>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-56">
        <DropdownMenuLabel className="flex flex-col gap-0.5">
          <span className="text-sm font-medium text-foreground">{user.username}</span>
          <span className="flex items-center gap-1 text-xs">
            <ShieldCheck className="h-3 w-3" /> {user.role.replace(/_/g, " ")}
          </span>
        </DropdownMenuLabel>
        <DropdownMenuSeparator />
        <DropdownMenuItem onClick={handleLogout}>
          <LogOut className="h-4 w-4" /> Log out
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
