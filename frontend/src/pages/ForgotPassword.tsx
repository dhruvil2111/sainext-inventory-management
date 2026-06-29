import { useState } from "react";
import { Link } from "react-router-dom";
import { Button } from "@/components/ui";

export default function ForgotPassword() {
  const [email, setEmail] = useState("");
  const [sent, setSent] = useState(false);

  return (
    <div className="flex min-h-screen items-center justify-center bg-brand p-4">
      <div className="w-full max-w-md">
        <div className="mb-6 flex items-center justify-center gap-3">
          <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-accent text-2xl font-black text-accent-fg">S</div>
          <h1 className="text-3xl font-extrabold text-brand-fg">Sainext</h1>
        </div>
        <div className="card p-6">
          <h2 className="mb-1 text-lg font-bold text-ink">Reset password</h2>
          {sent ? (
            <p className="mt-3 rounded-lg bg-success/10 px-3 py-2 text-sm text-success">
              If an account exists for <b>{email}</b>, your administrator has been
              notified to issue a reset. (Self-service email reset is planned for a
              later release.)
            </p>
          ) : (
            <>
              <p className="mb-5 text-sm text-muted">
                Enter your email and your administrator will help you reset access.
              </p>
              <form onSubmit={(e) => { e.preventDefault(); setSent(true); }} className="space-y-4">
                <div>
                  <label className="label">Email</label>
                  <input className="input" type="email" value={email}
                    onChange={(e) => setEmail(e.target.value)} required autoFocus />
                </div>
                <Button type="submit" className="w-full">Request reset</Button>
              </form>
            </>
          )}
          <div className="mt-5 border-t border-line pt-4 text-center">
            <Link to="/login" className="text-sm font-medium text-accent hover:underline">← Back to sign in</Link>
          </div>
        </div>
      </div>
    </div>
  );
}
