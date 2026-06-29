import { useEffect, useState } from "react";
import { Sun, Moon } from "@phosphor-icons/react";

const KEY = "sainext_theme";

function initialDark(): boolean {
  const saved = localStorage.getItem(KEY);
  if (saved === "light") return false;
  if (saved === "dark") return true;
  return !document.documentElement.classList.contains("light"); // default dark
}

export function ThemeToggle() {
  const [dark, setDark] = useState(initialDark);

  useEffect(() => {
    document.documentElement.classList.toggle("dark", dark);
    document.documentElement.classList.toggle("light", !dark);
    localStorage.setItem(KEY, dark ? "dark" : "light");
  }, [dark]);

  return (
    <button
      onClick={() => setDark((d) => !d)}
      className="rounded-md p-2 text-muted transition hover:bg-surface-2 hover:text-ink"
      title="Toggle theme"
    >
      {dark ? <Sun size={18} weight="fill" /> : <Moon size={18} weight="fill" />}
    </button>
  );
}
