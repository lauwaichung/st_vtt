export type Theme = 'light' | 'dark';

export function currentTheme(): Theme {
  return (document.documentElement.dataset.theme as Theme) || 'light';
}

export function setTheme(t: Theme): void {
  document.documentElement.dataset.theme = t;
  try { localStorage.setItem('theme', t); } catch {}
}

export function toggleTheme(): Theme {
  const t: Theme = currentTheme() === 'dark' ? 'light' : 'dark';
  setTheme(t);
  return t;
}
