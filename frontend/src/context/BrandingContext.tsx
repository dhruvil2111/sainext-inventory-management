import { createContext, useContext, useEffect, useState, useCallback, ReactNode } from "react";
import { api } from "@/lib/api";
import { applyBranding, Branding } from "@/lib/branding";

interface BrandingCtx {
  branding: Branding;
  reload: () => void;
}

const Ctx = createContext<BrandingCtx>({ branding: {}, reload: () => {} });
export const useBranding = () => useContext(Ctx);

export function BrandingProvider({ children }: { children: ReactNode }) {
  const [branding, setBranding] = useState<Branding>({});

  const reload = useCallback(() => {
    api.get("/settings/branding")
      .then((d) => { setBranding(d); applyBranding(d); })
      .catch(() => {});
  }, []);

  useEffect(() => { reload(); }, [reload]);

  return <Ctx.Provider value={{ branding, reload }}>{children}</Ctx.Provider>;
}
