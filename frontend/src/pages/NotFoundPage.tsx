import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";

export function NotFoundPage() {
  return (
    <div className="flex h-screen flex-col items-center justify-center gap-3 text-center">
      <span className="font-display text-5xl font-semibold">404</span>
      <p className="text-sm text-muted-foreground">This page doesn't exist.</p>
      <Button asChild variant="outline" size="sm">
        <Link to="/playground">Back to Playground</Link>
      </Button>
    </div>
  );
}
