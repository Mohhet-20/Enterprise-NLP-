import { useLocation } from "react-router-dom";
import { ChevronRight } from "lucide-react";
import { navItems } from "@/components/layout/nav-config";

export function Breadcrumbs() {
  const location = useLocation();

  // Exact match first (covers "/"), then the longest matching prefix —
  // "/datasets/abc-123" should resolve to the "Datasets" nav item, not
  // show "Not found" just because it isn't itself a registered nav path.
  const exactMatch = navItems.find((item) => item.path === location.pathname);
  const prefixMatch = navItems
    .filter((item) => item.path !== "/" && location.pathname.startsWith(item.path))
    .sort((a, b) => b.path.length - a.path.length)[0];
  const current = exactMatch ?? prefixMatch;

  return (
    <div className="flex items-center gap-1.5 text-sm text-muted-foreground">
      <span>NLP Platform</span>
      <ChevronRight className="h-3.5 w-3.5" />
      <span className="font-medium text-foreground">{current?.label ?? "Not found"}</span>
    </div>
  );
}
