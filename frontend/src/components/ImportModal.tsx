import { useRef, useState } from "react";
import { DownloadSimple, UploadSimple, CheckCircle, WarningCircle } from "@phosphor-icons/react";
import { api } from "@/lib/api";
import { useToast } from "@/context/ToastContext";
import { Modal, Button, Spinner } from "@/components/ui";

interface Result { created: number; failed: number; errors: { row: number; message: string }[]; }

export function ImportModal({ title, templatePath, importPath, onClose, onDone }: {
  title: string; templatePath: string; importPath: string;
  onClose: () => void; onDone: () => void;
}) {
  const { push } = useToast();
  const fileRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<Result | null>(null);

  const run = async () => {
    if (!file) return push("Choose a CSV file first", "error");
    setBusy(true); setResult(null);
    try {
      const r = await api.upload(importPath, file);
      setResult(r);
      if (r.created > 0) { push(`Imported ${r.created} row(s)`, "success"); onDone(); }
      if (r.created === 0 && r.failed > 0) push("No rows imported — see errors", "error");
    } catch (e: any) { push(e.message, "error"); }
    finally { setBusy(false); }
  };

  return (
    <Modal open onClose={onClose} title={title}
      footer={<>
        <Button variant="ghost" onClick={onClose}>Close</Button>
        <Button onClick={run} disabled={busy || !file}>{busy ? <Spinner className="h-4 w-4" /> : "Import"}</Button>
      </>}>
      <div className="space-y-4">
        <ol className="space-y-2 text-sm text-muted">
          <li className="flex items-center gap-2">
            <span className="flex h-5 w-5 items-center justify-center rounded-full bg-surface-2 text-2xs font-bold text-ink">1</span>
            Download the template and fill in your rows.
          </li>
          <li className="flex items-center gap-2">
            <span className="flex h-5 w-5 items-center justify-center rounded-full bg-surface-2 text-2xs font-bold text-ink">2</span>
            Upload the completed CSV. Invalid rows are reported and skipped.
          </li>
        </ol>

        <Button variant="outline" onClick={() => api.download(templatePath, "template.csv").catch((e) => push(e.message, "error"))}>
          <DownloadSimple size={16} weight="bold" /> Download template
        </Button>

        <div>
          <input ref={fileRef} type="file" accept=".csv,text/csv" className="hidden"
            onChange={(e) => { setFile(e.target.files?.[0] || null); setResult(null); }} />
          <button type="button" onClick={() => fileRef.current?.click()}
            className="flex w-full items-center justify-center gap-2 rounded-sm border border-dashed border-line-strong bg-surface-2 px-4 py-6 text-sm text-muted transition hover:border-accent/50 hover:text-ink">
            <UploadSimple size={18} weight="bold" />
            {file ? file.name : "Choose CSV file…"}
          </button>
        </div>

        {result && (
          <div className="rounded-sm border border-line p-3 text-sm">
            <div className="flex items-center gap-4">
              <span className="flex items-center gap-1.5 text-success"><CheckCircle size={16} weight="fill" /> {result.created} created</span>
              {result.failed > 0 && <span className="flex items-center gap-1.5 text-danger"><WarningCircle size={16} weight="fill" /> {result.failed} failed</span>}
            </div>
            {result.errors.length > 0 && (
              <div className="mt-2 max-h-40 overflow-y-auto">
                {result.errors.map((er, i) => (
                  <div key={i} className="border-t border-line py-1 text-xs text-muted">
                    Row {er.row}: <span className="text-danger">{er.message}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </Modal>
  );
}
