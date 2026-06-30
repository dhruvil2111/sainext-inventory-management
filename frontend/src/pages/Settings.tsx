import { FormEvent, useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { useBranding } from "@/context/BrandingContext";
import { useToast } from "@/context/ToastContext";
import { applyBranding } from "@/lib/branding";
import { PageHeader } from "@/components/layout/PageHeader";
import { Card, Button, Spinner } from "@/components/ui";
import { Gear, UploadSimple, Trash } from "@phosphor-icons/react";

export default function Settings() {
  const { can } = useAuth();
  const { reload } = useBranding();
  const { push } = useToast();
  const [form, setForm] = useState<any>(null);
  const [saving, setSaving] = useState(false);
  const [logoBusy, setLogoBusy] = useState(false);
  const logoRef = useRef<HTMLInputElement>(null);
  const canEdit = can("Settings:edit");

  useEffect(() => {
    api.get("/settings").then(setForm).catch((e) => push(e.message, "error"));
  }, []); // eslint-disable-line

  const uploadLogo = async (f: File) => {
    setLogoBusy(true);
    try {
      const r = await api.upload("/settings/logo", f);
      setForm((prev: any) => ({ ...prev, company_logo: r.company_logo }));
      reload();
      push("Logo updated", "success");
    } catch (e: any) { push(e.message, "error"); }
    finally { setLogoBusy(false); }
  };

  const removeLogo = async () => {
    setLogoBusy(true);
    try {
      await api.del("/settings/logo");
      setForm((prev: any) => ({ ...prev, company_logo: null }));
      reload();
      push("Logo removed", "success");
    } catch (e: any) { push(e.message, "error"); }
    finally { setLogoBusy(false); }
  };

  const set = (k: string) => (e: any) => {
    const next = { ...form, [k]: e.target.value };
    setForm(next);
    if (k === "brand_primary" || k === "brand_accent" || k === "company_name") applyBranding(next);
  };

  const save = async (e: FormEvent) => {
    e.preventDefault();
    setSaving(true);
    try {
      for (const key of ["company_name", "currency", "brand_primary", "brand_accent"]) {
        await api.put("/settings", { key, value: form[key] });
      }
      applyBranding(form);
      push("Settings saved", "success");
    } catch (err: any) { push(err.message, "error"); }
    finally { setSaving(false); }
  };

  if (!form) return <Card><div className="p-6 text-center text-accent"><Spinner className="h-6 w-6" /></div></Card>;

  return (
    <div>
      <PageHeader icon={Gear} title="Settings" subtitle="Company profile and brand theme" />
      <Card className="max-w-xl p-6">
        <form onSubmit={save} className="space-y-4">
          <div>
            <label className="label">Company name</label>
            <input className="input" value={form.company_name || ""} onChange={set("company_name")} disabled={!canEdit} />
          </div>
          <div>
            <label className="label">Currency</label>
            <input className="input" value={form.currency || ""} onChange={set("currency")} disabled={!canEdit} />
          </div>

          <div>
            <label className="label">Company logo</label>
            <div className="flex items-center gap-4">
              <div className="flex h-16 w-16 shrink-0 items-center justify-center overflow-hidden rounded-xl border border-line bg-brand">
                {form.company_logo
                  ? <img src={form.company_logo} alt="Logo" className="h-full w-full object-contain" />
                  : <span className="text-2xs text-brand-fg/50">No logo</span>}
              </div>
              {canEdit && (
                <div className="flex flex-col gap-2">
                  <input ref={logoRef} type="file" accept="image/png,image/jpeg,image/svg+xml,image/webp,image/gif"
                    className="hidden" onChange={(e) => { const f = e.target.files?.[0]; if (f) uploadLogo(f); }} />
                  <div className="flex gap-2">
                    <Button type="button" variant="outline" className="!py-1.5" disabled={logoBusy}
                      onClick={() => logoRef.current?.click()}>
                      {logoBusy ? <Spinner className="h-4 w-4" /> : <><UploadSimple size={15} weight="bold" /> Upload</>}
                    </Button>
                    {form.company_logo && (
                      <Button type="button" variant="ghost" className="!py-1.5 text-danger" disabled={logoBusy}
                        onClick={removeLogo}><Trash size={15} weight="bold" /> Remove</Button>
                    )}
                  </div>
                  <p className="text-2xs text-muted">PNG, JPG, SVG, WEBP or GIF · max 1 MB. Shown in the sidebar and sign-in.</p>
                </div>
              )}
            </div>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="label">Primary (brand) color</label>
              <div className="flex items-center gap-3">
                <input type="color" value={form.brand_primary || "#1f2530"} onChange={set("brand_primary")}
                  disabled={!canEdit} className="h-10 w-14 rounded border border-line" />
                <span className="text-sm text-muted">{form.brand_primary}</span>
              </div>
            </div>
            <div>
              <label className="label">Accent color</label>
              <div className="flex items-center gap-3">
                <input type="color" value={form.brand_accent || "#f5a623"} onChange={set("brand_accent")}
                  disabled={!canEdit} className="h-10 w-14 rounded border border-line" />
                <span className="text-sm text-muted">{form.brand_accent}</span>
              </div>
            </div>
          </div>

          <div className="rounded-xl border border-line p-4">
            <div className="mb-2 text-xs uppercase text-muted">Live preview</div>
            <div className="flex flex-wrap items-center gap-2">
              <span className="rounded-lg bg-brand px-3 py-1.5 text-sm font-semibold text-brand-fg">Brand</span>
              <button type="button" className="btn-accent !py-1.5">Accent button</button>
              <span className="rounded-full bg-accent/20 px-2.5 py-0.5 text-xs font-semibold text-accent">badge</span>
            </div>
          </div>

          {canEdit
            ? <Button type="submit" disabled={saving}>{saving ? <Spinner /> : "Save settings"}</Button>
            : <p className="text-sm text-muted">You have read-only access to settings.</p>}
        </form>
      </Card>
    </div>
  );
}
