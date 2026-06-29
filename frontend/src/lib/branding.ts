// Apply brand colors (stored as hex in settings) to the CSS-variable theme.
// theme.css expects "R G B" channel triplets so Tailwind opacity modifiers work.
export interface Branding {
  company_name?: string;
  currency?: string;
  brand_primary?: string;
  brand_accent?: string;
}

function hexToTriplet(hex?: string): string | null {
  if (!hex) return null;
  const m = hex.replace("#", "");
  if (m.length !== 6) return null;
  const r = parseInt(m.slice(0, 2), 16);
  const g = parseInt(m.slice(2, 4), 16);
  const b = parseInt(m.slice(4, 6), 16);
  if ([r, g, b].some((n) => Number.isNaN(n))) return null;
  return `${r} ${g} ${b}`;
}

export function applyBranding(b: Branding) {
  const root = document.documentElement;
  const p = hexToTriplet(b.brand_primary);
  const a = hexToTriplet(b.brand_accent);
  if (p) root.style.setProperty("--c-primary", p);
  if (a) root.style.setProperty("--c-accent", a);
  if (b.company_name) document.title = b.company_name;
}
