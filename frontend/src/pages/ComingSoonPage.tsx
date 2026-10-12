import { useLocation } from "react-router-dom";
import { Construction } from "lucide-react";
import { navItems } from "@/components/layout/nav-config";
import { Card, CardContent } from "@/components/ui/card";

export function ComingSoonPage() {
  const location = useLocation();
  const item = navItems.find((n) => n.path === location.pathname);

  return (
    <div className="flex h-full items-center justify-center p-8">
      <Card className="max-w-md text-center">
        <CardContent className="flex flex-col items-center gap-3 pt-8">
          <div className="flex h-12 w-12 items-center justify-center rounded-full bg-muted">
            <Construction className="h-5 w-5 text-muted-foreground" />
          </div>
          <h2 className="font-display text-lg font-semibold">{item?.label ?? "This page"} isn't built yet</h2>
          <p className="text-sm text-muted-foreground">
            {item?.description.replace(" — coming soon", "") ??
              "This section of the platform hasn't been implemented in this build."}{" "}
            This stage of the project focused on the app shell and the
            Inference Playground — this page is next in line.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
