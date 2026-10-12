import {
  LayoutDashboard,
  FlaskConical,
  Boxes,
  Database,
  ClipboardList,
  LineChart,
  ShieldCheck,
  Sparkles,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";

export interface NavItem {
  label: string;
  path: string;
  icon: LucideIcon;
  implemented: boolean;
  description: string;
}

export const navItems: NavItem[] = [
  {
    label: "Overview",
    path: "/",
    icon: LayoutDashboard,
    implemented: true,
    description: "Real-time KPIs aggregated from the live API",
  },
  {
    label: "Playground",
    path: "/playground",
    icon: FlaskConical,
    implemented: true,
    description: "Run live predictions against registered models",
  },
  {
    label: "Datasets",
    path: "/datasets",
    icon: Database,
    implemented: true,
    description: "Upload, validate, profile, and version datasets",
  },
  {
    label: "Models",
    path: "/models",
    icon: Boxes,
    implemented: true,
    description: "Register, approve, promote, and deploy model versions",
  },
  {
    label: "Evaluations",
    path: "/evaluations",
    icon: ClipboardList,
    implemented: true,
    description: "Run evaluations and review error analysis",
  },
  {
    label: "Monitoring",
    path: "/monitoring",
    icon: LineChart,
    implemented: false,
    description: "Live model monitoring — coming soon",
  },
  {
    label: "Admin",
    path: "/admin",
    icon: ShieldCheck,
    implemented: false,
    description: "Users, roles & audit logs — coming soon",
  },
];

export const copilotItem: NavItem = {
  label: "Copilot",
  path: "/copilot",
  icon: Sparkles,
  implemented: false,
  description: "AI assistant — coming soon",
};
