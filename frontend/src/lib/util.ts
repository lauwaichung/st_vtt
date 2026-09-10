import type { ContentPack, Move, Playbook, CharacterDoc } from './types';

export function levelUpCost(formula: string, level: number): number {
  if (!/^[0-9+\-*/() level]*$/.test(formula)) return Infinity;
  try { return Math.floor(Function('level', `return (${formula});`)(level)); } catch { return Infinity; }
}

export function fmtMod(n: number): string {
  return n >= 0 ? `+${n}` : `${n}`;
}

export function playbookOf(content: ContentPack, doc: CharacterDoc): Playbook | undefined {
  return content.playbooks.find((p) => p.id === doc.playbook);
}

/** All moves a character could know: shared + playbook + arcana-on-sheet + custom. */
export function moveIndex(content: ContentPack, doc: CharacterDoc, pb: Playbook | undefined): Map<string, Move> {
  const idx = new Map<string, Move>();
  for (const group of Object.values(content.moves)) for (const m of group) idx.set(m.id, m);
  if (pb) for (const m of pb.moves) idx.set(m.id, m);
  for (const a of doc.arcana || []) for (const m of a.moves || []) idx.set(m.id, m);
  for (const m of doc.custom_moves || []) idx.set(m.id, m);
  return idx;
}

export function timeShort(ts: number): string {
  const d = new Date(ts * 1000);
  return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

export function uid(): string {
  return Math.random().toString(36).slice(2, 10);
}

export function download(filename: string, data: unknown): void {
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

export function pickFile(accept = '.json'): Promise<unknown> {
  return new Promise((resolve, reject) => {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = accept;
    input.onchange = async () => {
      const f = input.files?.[0];
      if (!f) return reject(new Error('no file'));
      try { resolve(JSON.parse(await f.text())); } catch (e) { reject(e); }
    };
    input.click();
  });
}

/** Deterministic, readable color per user name (hsl hue from a string hash). */
export function userColor(name: string): string {
  let h = 0;
  for (let i = 0; i < name.length; i++) h = (h * 31 + name.charCodeAt(i)) >>> 0;
  return `hsl(${h % 360} 65% 45%)`;
}

export function presenceKey(entity: string, id: string, path: string): string {
  return `${entity}/${id}${path}`;
}
