import { ReactNode } from "react";
import { Navigate, useLocation } from "react-router-dom";
import { Prohibit } from "@phosphor-icons/react";
import { useAuth } from "@/context/AuthContext";
import { Spinner, EmptyState } from "@/components/ui";

export function RequireAuth({ children }: { children: ReactNode }) {
  const { user, loading } = useAuth();
  const loc = useLocation();
  if (loading)
    return (
      <div className="flex h-screen items-center justify-center text-accent">
        <Spinner className="h-8 w-8" />
      </div>
    );
  if (!user) return <Navigate to="/login" state={{ from: loc }} replace />;
  return <>{children}</>;
}

export function RequirePermission({ code, children }: { code: string; children: ReactNode }) {
  const { can } = useAuth();
  if (!can(code))
    return (
      <EmptyState
        icon={<Prohibit size={22} weight="duotone" />}
        title="No access"
        hint="You don't have permission to view this page. Contact your administrator if you believe this is an error."
      />
    );
  return <>{children}</>;
}
