import { createBrowserRouter, Navigate } from "react-router-dom";
import { AppShell } from "@/components/layout/AppShell";
import { ProtectedRoute } from "@/routes/ProtectedRoute";
import { LoginPage } from "@/pages/LoginPage";
import { RegisterPage } from "@/pages/RegisterPage";
import { PlaygroundPage } from "@/pages/PlaygroundPage";
import { DashboardPage } from "@/pages/DashboardPage";
import { DatasetsPage } from "@/pages/DatasetsPage";
import { DatasetDetailPage } from "@/pages/DatasetDetailPage";
import { ModelsPage } from "@/pages/ModelsPage";
import { EvaluationsPage } from "@/pages/EvaluationsPage";
import { EvaluationDetailPage } from "@/pages/EvaluationDetailPage";
import { ComingSoonPage } from "@/pages/ComingSoonPage";
import { NotFoundPage } from "@/pages/NotFoundPage";

export const router = createBrowserRouter([
  { path: "/login", element: <LoginPage /> },
  { path: "/register", element: <RegisterPage /> },
  {
    element: <ProtectedRoute />,
    children: [
      {
        element: <AppShell />,
        children: [
          { path: "/", element: <DashboardPage /> },
          { path: "/playground", element: <PlaygroundPage /> },
          { path: "/models", element: <ModelsPage /> },
          { path: "/datasets", element: <DatasetsPage /> },
          { path: "/datasets/:id", element: <DatasetDetailPage /> },
          { path: "/evaluations", element: <EvaluationsPage /> },
          { path: "/evaluations/:runId", element: <EvaluationDetailPage /> },
          { path: "/monitoring", element: <ComingSoonPage /> },
          { path: "/admin", element: <ComingSoonPage /> },
          { path: "/copilot", element: <ComingSoonPage /> },
        ],
      },
    ],
  },
  { path: "/404", element: <NotFoundPage /> },
  { path: "*", element: <Navigate to="/404" replace /> },
]);
