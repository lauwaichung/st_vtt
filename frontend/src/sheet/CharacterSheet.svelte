<script lang="ts">
  import { setContext } from 'svelte';
  import { app, canEdit, isGm } from '../lib/state.svelte';
  import { characterPatcher, SHEET } from '../lib/patch';
  import { api } from '../lib/api';
  import { toast } from '../lib/state.svelte';
  import { download, playbookOf } from '../lib/util';
  import type { CharacterRow, Section } from '../lib/types';
  import Collapsible from '../ui/Collapsible.svelte';
  import Confirm from '../ui/Confirm.svelte';
  import Identity from './sections/Identity.svelte';
  import Stats from './sections/Stats.svelte';
  import Moves from './sections/Moves.svelte';
  import Gear from './sections/Gear.svelte';
  import Followers from './sections/Followers.svelte';
  import Arcana from './sections/Arcana.svelte';
  import Notes from './sections/Notes.svelte';
  import GenericSection from './sections/GenericSection.svelte';

  let { row }: { row: CharacterRow } = $props();
  const content = $derived(app.content!);
  const doc = $derived(row.data);
  const pb = $derived(playbookOf(content, doc));
  const editable = $derived(canEdit(row));
  const p = characterPatcher(row.id);
  setContext(SHEET, { entity: 'character', id: row.id, p });
  let confirmDelete = $state(false);

  const checklist = $derived.by((): string[] => {
    const items: string[] = [];
    if (!doc.name?.trim()) items.push('Choose a name');
    const arr = pb?.stat_array ?? content.pack.stat_array;
    if (arr.length) {
      const have = Object.values(doc.stats ?? {}).slice().sort((a, b) => a - b).join(',');
      const want = arr.slice().sort((a, b) => a - b).join(',');
      if (have !== want) items.push(`Assign stats from ${arr.map((n) => (n >= 0 ? '+' + n : n)).join(', ')}`);
    }
    for (const sec of pb?.sections ?? []) {
      if (!sec.required) continue;
      const v = doc.sections?.[sec.id];
      if (sec.type === 'choose' && (v === null || v === undefined || v === '')) items.push(`Choose ${sec.title.toLowerCase()}`);
      else if (sec.type === 'multichoose') {
        const need = (sec.min ?? 1) - ((v as string[])?.length ?? 0);
        if (need > 0) items.push(`${sec.title}: pick ${need} more`);
      } else if (sec.type === 'checklist' && !((v as string[])?.length)) items.push(`${sec.title}: check at least one`);
      else if (sec.type === 'text' && !String(v ?? '').trim()) items.push(`Fill in ${sec.title.toLowerCase()}`);
      else if (sec.type === 'table' && !((v as unknown[])?.length)) items.push(`${sec.title}: add at least one row`);
    }
    for (const c of pb?.starting_moves.choose ?? []) {
      const have = c.from.filter((id) => doc.moves.taken.includes(id)).length;
      if (have < c.n) items.push(`Choose ${c.n - have} more starting move${c.n - have > 1 ? 's' : ''} (${c.from.map((id) => pb?.moves.find((m) => m.id === id)?.name ?? id).join(' / ')}) using + Move in the Moves section`);
    }
    return items;
  });

  // Once every creation item is satisfied, mark creation done so the checklist stays hidden.
  $effect(() => {
    if (editable && !doc.creation_done && checklist.length === 0) p('/creation_done', true);
  });

  async function exportJson() {
    try { download(`${doc.name || 'character'}.json`, await api.get(`/api/characters/${row.id}/export`)); } catch (e) { toast((e as Error).message, 'error'); }
  }
  async function remove() {
    try { await api.del(`/api/characters/${row.id}`); } catch (e) { toast((e as Error).message, 'error'); }
  }
  async function setOwner(e: Event) {
    const owner = (e.target as HTMLSelectElement).value || null;
    try { await api.post(`/api/characters/${row.id}/owner`, { owner }); } catch (err) { toast((err as Error).message, 'error'); }
  }
  const inserts = $derived(pb?.inserts ?? ['gear']);
</script>

<Collapsible id="char.{row.id}" title={doc.name || '(unnamed)'} level={2} subtitle="{pb?.name ?? doc.playbook} · {row.owner ?? 'unowned'}">
  {#snippet right()}
    {#if isGm()}
      <select class="small" value={row.owner ?? ''} onchange={setOwner} title="Owner">
        <option value="">(nobody)</option>
        {#each app.users as u}<option value={u.name}>{u.name}</option>{/each}
      </select>
    {/if}
    <button class="ghost small" onclick={exportJson} title="Export JSON">⇩</button>
    {#if editable}<button class="ghost small danger" onclick={() => (confirmDelete = true)} title="Delete">🗑</button>{/if}
  {/snippet}

  {#if !pb}
    <p class="muted">Unknown playbook <code>{doc.playbook}</code>: the content pack has no definition for it, so only core sections are shown.</p>
  {/if}

  {#if editable && !doc.creation_done && checklist.length}
    <div class="checklist">
      <strong>Character creation</strong>
      <ul>{#each checklist as item}<li>{item}</li>{/each}</ul>
      <button class="small" onclick={() => p('/creation_done', true)}>Hide checklist</button>
    </div>
  {/if}

  <Identity {doc} {p} {editable} {pb} />
  <Stats {doc} {p} {editable} {pb} />

  {#each pb?.sections ?? [] as sec (sec.id)}
    <GenericSection section={sec} value={doc.sections?.[sec.id]} {editable} basePath={`/sections/${sec.id}`} {doc} {p} />
  {/each}

  <Moves {doc} {p} {editable} {pb} characterId={row.id} />
  {#if inserts.includes('gear')}<Gear {doc} {p} {editable} />{/if}
  {#if inserts.includes('followers')}<Followers {doc} {p} {editable} />{/if}
  {#if inserts.includes('arcana')}<Arcana {doc} {p} {editable} characterId={row.id} />{/if}
  <Notes {doc} {p} {editable} id={row.id} />
</Collapsible>

{#if confirmDelete}
  <Confirm title="Delete {doc.name || 'this character'}?" text="Export it first if you want a backup." onyes={remove} onclose={() => (confirmDelete = false)} />
{/if}

<style>
  .checklist { background: var(--accent-soft); border-radius: 6px; padding: .5em .75em; margin: .25em 0 .5em; }
  .checklist ul { margin: .25em 0 .5em; }
</style>
