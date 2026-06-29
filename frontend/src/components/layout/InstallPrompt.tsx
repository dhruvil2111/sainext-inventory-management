import { useEffect, useState } from "react";
import { DownloadSimple, X, ShareNetwork, Cube } from "@phosphor-icons/react";
import { Button } from "@/components/ui";

const DISMISS_KEY = "sainext_install_dismissed";

function isIos() {
  return /iphone|ipad|ipod/i.test(navigator.userAgent);
}
function isStandalone() {
  return window.matchMedia("(display-mode: standalone)").matches ||
    (navigator as any).standalone === true;
}

export function InstallPrompt() {
  const [deferred, setDeferred] = useState<any>(null);
  const [show, setShow] = useState(false);
  const [ios, setIos] = useState(false);

  useEffect(() => {
    if (localStorage.getItem(DISMISS_KEY) || isStandalone()) return;
    const onBip = (e: any) => { e.preventDefault(); setDeferred(e); setShow(true); };
    window.addEventListener("beforeinstallprompt", onBip);
    if (isIos()) { setIos(true); setShow(true); }   // iOS never fires the event
    return () => window.removeEventListener("beforeinstallprompt", onBip);
  }, []);

  if (!show) return null;

  const dismiss = () => { setShow(false); localStorage.setItem(DISMISS_KEY, "1"); };
  const install = async () => {
    if (!deferred) return;
    deferred.prompt();
    await deferred.userChoice;
    setDeferred(null);
    dismiss();
  };

  return (
    <div className="fixed inset-x-4 bottom-20 z-40 md:inset-x-auto md:bottom-5 md:right-5 md:w-80"
      style={{ paddingBottom: "env(safe-area-inset-bottom)" }}>
      <div className="card flex items-start gap-3 p-3.5 shadow-pop">
        <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-accent text-accent-fg">
          <Cube size={18} weight="fill" />
        </span>
        <div className="min-w-0 flex-1">
          <p className="text-sm font-semibold text-ink">Install Sainext</p>
          {ios ? (
            <p className="mt-0.5 text-xs leading-relaxed text-muted">
              Tap <ShareNetwork size={12} className="inline -mt-0.5" weight="bold" /> Share, then
              <b className="text-ink"> Add to Home Screen</b>.
            </p>
          ) : (
            <p className="mt-0.5 text-xs leading-relaxed text-muted">Add it to your home screen for a full-screen, app-like experience.</p>
          )}
          {!ios && (
            <Button className="mt-2 !py-1.5 text-xs" onClick={install}>
              <DownloadSimple size={14} weight="bold" /> Install app
            </Button>
          )}
        </div>
        <button onClick={dismiss} className="rounded-md p-1 text-muted hover:bg-surface-2 hover:text-ink">
          <X size={16} weight="bold" />
        </button>
      </div>
    </div>
  );
}
