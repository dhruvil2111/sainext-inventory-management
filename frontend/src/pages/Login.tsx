import { FormEvent, useState } from "react";
import { useNavigate, useLocation, Link } from "react-router-dom";
import { Cube, Lightning, ShieldCheck, Stack, ArrowRight } from "@phosphor-icons/react";
import { useAuth } from "@/context/AuthContext";
import { useBranding } from "@/context/BrandingContext";
import { Button, Spinner } from "@/components/ui";

const DEMO = [
  ["Owner", "owner@sainext.app", "Owner@123"],
  ["Admin", "admin@sainext.app", "Admin@123"],
  ["Manager", "manager@sainext.app", "Manager@123"],
  ["Salesman", "salesman@sainext.app", "Sales@123"],
];

const HIGHLIGHTS = [
  { icon: Stack, label: "Real-time stock check across every warehouse" },
  { icon: Lightning, label: "Old-stock-first allocation with minimum wastage" },
  { icon: ShieldCheck, label: "Role-based access and full audit trail" },
];

export default function Login() {
  const { login } = useAuth();
  const { branding } = useBranding();
  const name = branding.company_name || "Sainext";
  const navigate = useNavigate();
  const loc = useLocation() as any;
  const [email, setEmail] = useState("owner@sainext.app");
  const [password, setPassword] = useState("Owner@123");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setError(""); setBusy(true);
    try {
      await login(email, password);
      navigate(loc.state?.from?.pathname || "/", { replace: true });
    } catch (err: any) {
      setError(err.message || "Login failed");
    } finally { setBusy(false); }
  };

  return (
    <div className="grid min-h-[100dvh] lg:grid-cols-2">
      {/* Brand panel */}
      <div className="relative hidden flex-col justify-between overflow-hidden bg-brand p-12 lg:flex">
        <div
          className="pointer-events-none absolute inset-0 opacity-[0.5]"
          style={{ background: "radial-gradient(600px circle at 30% 20%, rgb(var(--c-accent) / 0.16), transparent 55%), radial-gradient(500px circle at 80% 90%, rgb(var(--c-accent) / 0.1), transparent 50%)" }}
        />
        <div className="relative flex items-center gap-2.5">
          {branding.company_logo ? (
            <img src={branding.company_logo} alt={name} className="h-9 w-9 rounded-lg object-contain" />
          ) : (
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-accent text-accent-fg">
              <Cube size={20} weight="fill" />
            </div>
          )}
          <span className="text-lg font-bold tracking-tight text-brand-fg">{name}</span>
        </div>

        <div className="relative max-w-md">
          <h1 className="text-3xl font-semibold leading-tight tracking-tight text-brand-fg">
            Inventory, blocking and orders in one operational view.
          </h1>
          <div className="mt-8 space-y-4">
            {HIGHLIGHTS.map((h) => (
              <div key={h.label} className="flex items-center gap-3 text-sm text-brand-fg/70">
                <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-white/8 text-accent">
                  <h.icon size={17} weight="fill" />
                </span>
                {h.label}
              </div>
            ))}
          </div>
        </div>

        <div className="relative text-2xs text-brand-fg/40">Internal operations platform · v0.1</div>
      </div>

      {/* Form panel */}
      <div className="flex items-center justify-center bg-bg p-6">
        <div className="w-full max-w-sm">
          <div className="mb-8 lg:hidden">
            <div className="flex items-center gap-2.5">
              {branding.company_logo ? (
                <img src={branding.company_logo} alt={name} className="h-9 w-9 rounded-lg object-contain" />
              ) : (
                <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-accent text-accent-fg">
                  <Cube size={20} weight="fill" />
                </div>
              )}
              <span className="text-lg font-bold tracking-tight text-ink">{name}</span>
            </div>
          </div>

          <h2 className="text-xl font-semibold tracking-tight text-ink">Sign in</h2>
          <p className="mt-1 text-sm text-muted">Welcome back. Enter your credentials to continue.</p>

          <form onSubmit={submit} className="mt-7 space-y-4">
            <div>
              <label className="label">Email</label>
              <input className="input" type="email" value={email}
                onChange={(e) => setEmail(e.target.value)} required autoFocus />
            </div>
            <div>
              <label className="label">Password</label>
              <input className="input" type="password" value={password}
                onChange={(e) => setPassword(e.target.value)} required />
            </div>
            {error && (
              <p className="rounded-sm border border-danger/20 bg-danger/10 px-3 py-2 text-sm text-danger">{error}</p>
            )}
            <Button type="submit" disabled={busy} className="w-full">
              {busy ? <Spinner className="h-4 w-4" /> : <>Sign in <ArrowRight size={16} weight="bold" /></>}
            </Button>
          </form>

          <div className="mt-7 rounded-lg border border-line bg-surface p-4">
            <p className="mb-2.5 text-2xs font-semibold uppercase tracking-wider text-muted">Demo accounts</p>
            <div className="flex flex-wrap gap-1.5">
              {DEMO.map(([role, em, pw]) => (
                <button key={em} type="button"
                  onClick={() => { setEmail(em); setPassword(pw); }}
                  className="rounded-full border border-line bg-surface-2 px-2.5 py-1 text-2xs font-medium text-ink transition hover:border-accent/40 hover:text-accent-strong">
                  {role}
                </button>
              ))}
            </div>
          </div>

          <div className="mt-4 text-center">
            <Link to="/forgot-password" className="text-xs font-medium text-muted hover:text-accent-strong">Forgot password?</Link>
          </div>
        </div>
      </div>
    </div>
  );
}
