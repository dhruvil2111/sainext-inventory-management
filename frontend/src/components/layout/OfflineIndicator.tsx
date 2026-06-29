import { useEffect, useState } from "react";
import { WifiSlash } from "@phosphor-icons/react";

export function OfflineIndicator() {
  const [offline, setOffline] = useState(!navigator.onLine);
  useEffect(() => {
    const on = () => setOffline(false);
    const off = () => setOffline(true);
    window.addEventListener("online", on);
    window.addEventListener("offline", off);
    return () => { window.removeEventListener("online", on); window.removeEventListener("offline", off); };
  }, []);
  if (!offline) return null;
  return (
    <div className="flex items-center justify-center gap-2 bg-warning/15 py-1.5 text-xs font-medium text-warning">
      <WifiSlash size={14} weight="bold" /> Offline — showing last synced data
    </div>
  );
}
