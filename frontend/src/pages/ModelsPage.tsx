import { useState } from "react";
import { toast } from "sonner";
import { Boxes, Check, ChevronDown, Crown, Plus, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogTrigger,
} from "@/components/ui/dialog";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
  DropdownMenuSeparator,
} from "@/components/ui/dropdown-menu";
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from "@/components/ui/table";
import { TaskSelector } from "@/components/playground/TaskSelector";
import {
  useApproveModel,
  useDeployModel,
  useModels,
  useRegisterModel,
  useRejectModel,
  usePromoteModel,
  useSetChampion,
} from "@/hooks/useModels";
import { useAuthStore } from "@/stores/useAuthStore";
import { canApproveModels, hasPermission } from "@/lib/permissions";
import type { ApprovalStatus, DeploymentStatus, ModelLifecycleStage, NLPTask } from "@/types/api";

const APPROVAL_VARIANT: Record<ApprovalStatus, "default" | "secondary" | "destructive"> = {
  approved: "default",
  pending: "secondary",
  rejected: "destructive",
};
const DEPLOYMENT_VARIANT: Record<DeploymentStatus, "default" | "outline" | "secondary"> = {
  deployed: "default",
  not_deployed: "outline",
  rolled_back: "secondary",
};

function RegisterModelDialog() {
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");
  const [task, setTask] = useState<NLPTask>("sentiment_analysis");
  const [architecture, setArchitecture] = useState("custom");
  const [version, setVersion] = useState("1.0.0");
  const [modelPath, setModelPath] = useState("lexicon-baseline-v1");
  const register = useRegisterModel();

  async function handleRegister() {
    if (!name.trim()) return;
    try {
      await register.mutateAsync({ name: name.trim(), task, architecture, version, model_name_or_path: modelPath });
      toast.success(`Registered ${name.trim()} v${version}`);
      setOpen(false);
      setName("");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Registration failed");
    }
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button>
          <Plus className="h-4 w-4" /> Register Model
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Register a model version</DialogTitle>
          <DialogDescription>Starts in development, pending approval — nothing is deployed yet.</DialogDescription>
        </DialogHeader>
        <div className="flex flex-col gap-4">
          <div className="flex flex-col gap-1.5">
            <Label>Name</Label>
            <Input value={name} onChange={(e) => setName(e.target.value)} placeholder="sentiment-lexicon-baseline" />
          </div>
          <div className="flex flex-col gap-1.5">
            <Label>Task</Label>
            <TaskSelector value={task} onChange={setTask} />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div className="flex flex-col gap-1.5">
              <Label>Architecture</Label>
              <Input value={architecture} onChange={(e) => setArchitecture(e.target.value)} />
            </div>
            <div className="flex flex-col gap-1.5">
              <Label>Version</Label>
              <Input value={version} onChange={(e) => setVersion(e.target.value)} />
            </div>
          </div>
          <div className="flex flex-col gap-1.5">
            <Label>Model name / path</Label>
            <Input value={modelPath} onChange={(e) => setModelPath(e.target.value)} />
          </div>
          <Button onClick={handleRegister} disabled={!name.trim() || register.isPending} className="self-start">
            {register.isPending ? "Registering…" : "Register"}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}

export function ModelsPage() {
  const role = useAuthStore((s) => s.user?.role);
  const canWrite = hasPermission(role, "experiment:write");
  const canApprove = canApproveModels(role);

  const { data: models, isLoading } = useModels();
  const approve = useApproveModel();
  const reject = useRejectModel();
  const promote = usePromoteModel();
  const deploy = useDeployModel();
  const setChampion = useSetChampion();

  function handleAction(promise: Promise<unknown>, successMessage: string) {
    promise.then(() => toast.success(successMessage)).catch((err) => toast.error(err instanceof Error ? err.message : "Action failed"));
  }

  return (
    <div className="mx-auto flex max-w-6xl flex-col gap-6 p-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-display text-2xl font-semibold tracking-tight">Model Registry</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Register, approve, promote, and deploy model versions with a real approval lifecycle.
          </p>
        </div>
        {canWrite && <RegisterModelDialog />}
      </div>

      <Card>
        <CardContent className="p-0">
          {isLoading ? (
            <div className="flex flex-col gap-3 p-5">
              {[1, 2, 3].map((i) => (
                <Skeleton key={i} className="h-10 w-full" />
              ))}
            </div>
          ) : !models || models.length === 0 ? (
            <div className="flex flex-col items-center gap-2 p-12 text-center text-sm text-muted-foreground">
              <Boxes className="h-6 w-6" />
              <p>No models registered yet.</p>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Model</TableHead>
                  <TableHead>Task</TableHead>
                  <TableHead>Stage</TableHead>
                  <TableHead>Approval</TableHead>
                  <TableHead>Deployment</TableHead>
                  <TableHead>Metrics</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {models.map((model) => (
                  <TableRow key={model.id}>
                    <TableCell className="font-medium">
                      <div className="flex items-center gap-1.5">
                        {model.is_champion && <Crown className="h-3.5 w-3.5 text-warning" />}
                        {model.name}
                        <span className="text-xs text-muted-foreground">v{model.version}</span>
                      </div>
                    </TableCell>
                    <TableCell className="font-mono text-xs text-muted-foreground">{model.task}</TableCell>
                    <TableCell>
                      <Badge variant="outline">{model.stage}</Badge>
                    </TableCell>
                    <TableCell>
                      <Badge variant={APPROVAL_VARIANT[model.approval_status]}>{model.approval_status}</Badge>
                    </TableCell>
                    <TableCell>
                      <Badge variant={DEPLOYMENT_VARIANT[model.deployment_status]}>
                        {model.deployment_status.replace("_", " ")}
                      </Badge>
                    </TableCell>
                    <TableCell className="font-mono text-xs">
                      {model.accuracy != null ? `${(model.accuracy * 100).toFixed(1)}% acc` : "—"}
                    </TableCell>
                    <TableCell className="text-right">
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button variant="ghost" size="sm">
                            Actions <ChevronDown className="h-3.5 w-3.5" />
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end">
                          {canApprove && model.approval_status === "pending" && (
                            <>
                              <DropdownMenuItem
                                onClick={() => handleAction(approve.mutateAsync({ id: model.id }), "Model approved")}
                              >
                                <Check className="h-3.5 w-3.5" /> Approve
                              </DropdownMenuItem>
                              <DropdownMenuItem
                                onClick={() =>
                                  handleAction(reject.mutateAsync({ id: model.id, body: { reason: "Rejected via dashboard" } }), "Model rejected")
                                }
                              >
                                <X className="h-3.5 w-3.5" /> Reject
                              </DropdownMenuItem>
                              <DropdownMenuSeparator />
                            </>
                          )}
                          {canWrite && (
                            <>
                              <DropdownMenuItem
                                onClick={() =>
                                  handleAction(
                                    promote.mutateAsync({ id: model.id, stage: "staging" as ModelLifecycleStage }),
                                    "Promoted to staging"
                                  )
                                }
                                disabled={model.stage !== "development"}
                              >
                                Promote to staging
                              </DropdownMenuItem>
                              <DropdownMenuItem
                                onClick={() =>
                                  handleAction(
                                    promote.mutateAsync({ id: model.id, stage: "production" as ModelLifecycleStage }),
                                    "Promoted to production"
                                  )
                                }
                                disabled={model.approval_status !== "approved"}
                              >
                                Promote to production
                              </DropdownMenuItem>
                              <DropdownMenuItem
                                onClick={() => handleAction(deploy.mutateAsync({ id: model.id }), "Deployed")}
                                disabled={model.approval_status !== "approved" || model.stage !== "production"}
                              >
                                Deploy
                              </DropdownMenuItem>
                              <DropdownMenuItem
                                onClick={() => handleAction(setChampion.mutateAsync({ id: model.id }), "Set as champion")}
                                disabled={model.is_champion}
                              >
                                <Crown className="h-3.5 w-3.5" /> Set as champion
                              </DropdownMenuItem>
                            </>
                          )}
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
