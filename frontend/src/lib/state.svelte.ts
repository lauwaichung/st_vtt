import type { CharacterRow, ContentPack, Message, SharedRow, StateResponse, User } from './types';

export const app = $state({
  me: null as User | null,
  content: null as ContentPack | null,
  campaignName: '',
  users: [] as User[],
  online: [] as string[],
  characters: {} as Record<string, CharacterRow>,
  shared: {} as Record<string, SharedRow>,
  messages: [] as Message[],
  connected: false,
  loading: true,
  /** other clients' focused field, keyed by their client id */
  fieldPresence: {} as Record<string, { user: string; key: string }>,
  /** users currently typing in chat -> expiry timestamp (ms) */
  typing: {} as Record<string, number>,
  toast: null as { text: string; kind: 'error' | 'info' } | null,
  /** shown on the login page after being signed out, e.g. from another device */
  loginNotice: '' as string,
});

let toastTimer: ReturnType<typeof setTimeout> | null = null;
export function toast(text: string, kind: 'error' | 'info' = 'info') {
  app.toast = { text, kind };
  if (toastTimer) clearTimeout(toastTimer);
  toastTimer = setTimeout(() => (app.toast = null), kind === 'error' ? 6000 : 3000);
}

export function loadState(s: StateResponse) {
  app.me = s.me;
  app.campaignName = s.campaign_name;
  app.users = s.users;
  app.online = s.online;
  const chars: Record<string, CharacterRow> = {};
  for (const c of s.characters) chars[c.id] = c;
  app.characters = chars;
  const sh: Record<string, SharedRow> = {};
  for (const r of s.shared) sh[r.id] = r;
  app.shared = sh;
  app.messages = s.messages;
}

export const isGm = () => app.me?.role === 'gm';
export const myCharacters = () => Object.values(app.characters).filter((c) => c.owner === app.me?.name);
export const otherCharacters = () => Object.values(app.characters).filter((c) => c.owner !== app.me?.name);
export const canEdit = (row: CharacterRow) => isGm() || row.owner === app.me?.name;

export const sharedSheets = () => Object.values(app.shared).sort((a, b) => a.created_at - b.created_at);
