import {
  LayoutDashboard,
  FlaskConical,
  Boxes,
  Database,
  ClipboardList,
  LineChart,
  ShieldCheck,
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
    implemented: true,
    description: "Live inference traffic, latency, errors and host resources",
  },
  {
    label: "Admin",
    path: "/admin",
    icon: ShieldCheck,
    implemented: true,
    description: "Searchable audit trail of every privileged action",
  },
];
