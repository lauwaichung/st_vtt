<script lang="ts">
  // Renders a declarative content-pack section against a value stored in doc.sections[id].
  import type { CharacterDoc, Effects, Section, SharedDoc } from '../../lib/types';
  import { send } from '../../lib/ws';
  import type { Patcher } from '../../lib/patch';
  import Collapsible from '../../ui/Collapsible.svelte';
  import DebouncedText from '../../ui/DebouncedText.svelte';
  import Pips from '../../ui/Pips.svelte';
  import { getContext } from 'svelte';
  import { SHEET, type SheetContext } from '../../lib/patch';
  import { presence } from '../../lib/presence.svelte';

  let { section, value, editable, basePath, doc, p, idPrefix = '' }: {
    section: Section; value: unknown; editable: boolean; basePath: string;
    doc?: CharacterDoc | SharedDoc; p: Patcher; idPrefix?: string;
  } = $props();
  const onchange = (v: unknown) => p(basePath, v);

  const s = $derived(section);
  const sheet = getContext<SheetContext | undefined>(SHEET);
  const pres = (path: string) => (sheet ? { entity: sheet.entity, id: sheet.id, path } : undefined);
  const arr = $derived(Array.isArray(value) ? (value as any[]) : []);

  /** Apply (+1) or undo (-1) an option's effects on the character document. */
  function effects(e: Effects | null | undefined, sign: 1 | -1) {
    if (!e || !p || !doc || !('moves' in doc) || !('taken' in (doc as CharacterDoc).moves)) return;
    const c = doc as CharacterDoc;
    for (const id of e.moves) p('/moves/taken', id, sign > 0 ? 'list_add' : 'list_remove');
    if (e.armor) p('/armor', Math.max(0, (c.armor ?? 0) + sign * e.armor));
    if (e.hp) {
      p('/hp/max', Math.max(1, c.hp.max + sign * e.hp));
      p('/hp/current', Math.max(0, c.hp.current + sign * e.hp));
    }
  }

  function choose(id: string) {
    if (!editable) return;
    const prev = s.options.find((o) => o.id === value);
    const next = s.options.find((o) => o.id === id);
    if (prev?.id === id) return;
    effects(prev?.effects, -1);
    onchange(id);
    effects(next?.effects, 1);
  }
  function toggle(id: string, applyEffects: boolean) {
    if (!editable) return;
    const on = arr.includes(id);
    const opt = s.options.find((o) => o.id === id);
    if (!on && s.max != null && arr.length >= s.max) return;
    p(basePath, id, on ? 'list_remove' : 'list_add');
    if (applyEffects) effects(opt?.effects, on ? -1 : 1);
  }
  function setCell(i: number, col: string, v: unknown) {
    p(`${basePath}/${i}/${col}`, v);
  }
  function addRow() {
    const row: Record<string, unknown> = {};
    for (const c of s.columns) row[c.id] = c.type === 'check' ? false : c.type === 'number' ? 0 : '';
    p(`${basePath}/-`, row);
  }
  function removeRow(i: number) {
    p(`${basePath}/${i}`, null, 'remove');
  }
  function rollCell(row: Record<string, unknown>, col: { id: string; label: string }) {
    const expr = String(row[col.id] ?? '').trim();
    if (!expr) return;
    const first = s.columns.find((c) => c.type === 'text');
    const who = first ? String(row[first.id] ?? '').trim() : '';
    send({ type: 'roll', expr, label: [who, col.label].filter(Boolean).join(' · ') }).catch(() => {});
  }
  const optionPips = (oid: string) => Number(doc?.option_pips?.[s.id]?.[oid] ?? 0);
  const pickHint = $derived(
    s.type === 'multichoose' ? (s.min != null && s.max != null && s.min === s.max ? `pick ${s.min}` : s.min != null ? `pick ${s.min}+` : s.max != null ? `up to ${s.max}` : '') : '',
  );
</script>

<Collapsible id="{idPrefix}sec.{s.id}" title={s.title} subtitle={pickHint}>
  {#if s.help}<p class="muted small help">{s.help}</p>{/if}

  {#if s.type === 'choose'}
    <div class="opts">
      {#each s.options as o}
        <label class="opt" class:sel={value === o.id} class:ro={!editable}>
          <input type="radio" name="{sheet ? `${sheet.entity}.${sheet.id}.` : idPrefix}{s.id}" checked={value === o.id} disabled={!editable} use:presence={pres(basePath)} onchange={() => choose(o.id)} />
          <span><strong>{o.label}</strong>{#if o.text}<span class="muted">&nbsp;— {o.text}</span>{/if}</span>
          {#if o.pips && value === o.id}
            <Pips value={optionPips(o.id)} max={o.pips} onchange={(v) => p(`/option_pips/${s.id}/${o.id}`, v)} path={`/option_pips/${s.id}/${o.id}`} disabled={!editable} />
          {/if}
        </label>
      {/each}
    </div>

  {:else if s.type === 'multichoose' || s.type === 'checklist'}
    <div class="opts">
      {#each s.options as o}
        <label class="opt" class:sel={arr.includes(o.id)} class:ro={!editable}>
          <input type="checkbox" checked={arr.includes(o.id)} disabled={!editable || (!arr.includes(o.id) && s.max != null && arr.length >= s.max)}
            use:presence={pres(basePath)} onchange={() => toggle(o.id, s.type === 'multichoose')} />
          <span><strong>{o.label}</strong>{#if o.text}<span class="muted">&nbsp;— {o.text}</span>{/if}</span>
          {#if o.pips && arr.includes(o.id)}
            <Pips value={optionPips(o.id)} max={o.pips} onchange={(v) => p(`/option_pips/${s.id}/${o.id}`, v)} path={`/option_pips/${s.id}/${o.id}`} disabled={!editable} />
          {/if}
        </label>
      {/each}
    </div>

  {:else if s.type === 'pips'}
    <Pips value={Number(value) || 0} max={s.max ?? 1} onchange={(v) => onchange(v)} disabled={!editable} path={basePath} />

  {:else if s.type === 'text'}
    <DebouncedText multiline value={String(value ?? '')} path={basePath} readonly={!editable} placeholder={s.placeholder} />

  {:else if s.type === 'names'}
    <div class="stack">
      {#each s.lists as l}
        <div class="row">
          <span class="muted small listlbl">{l.label}</span>
          {#each l.names as n}
            <button class="small" class:primary={value === n} disabled={!editable} onclick={() => { onchange(n); p?.('/name', n); }}>{n}</button>
          {/each}
        </div>
      {/each}
    </div>

  {:else if s.type === 'table'}
    <div style="overflow-x:auto">
      <table class="grid">
        <thead><tr>{#each s.columns as c}<th>{c.label}</th>{/each}{#if editable}<th></th>{/if}</tr></thead>
        <tbody>
          {#each arr as row, i}
            <tr>
              {#each s.columns as c}
                <td>
                  {#if c.type === 'check'}
                    <input type="checkbox" checked={!!row[c.id]} disabled={!editable} use:presence={pres(`${basePath}/${i}/${c.id}`)} onchange={(e) => setCell(i, c.id, (e.target as HTMLInputElement).checked)} />
                  {:else if c.type === 'number'}
                    <input type="number" value={row[c.id] ?? 0} disabled={!editable} use:presence={pres(`${basePath}/${i}/${c.id}`)} onchange={(e) => setCell(i, c.id, Number((e.target as HTMLInputElement).value))} />
                  {:else if c.type === 'dice'}
                    <span class="row" style="gap:.3em;flex-wrap:nowrap">
                      <DebouncedText class="kbd dice" value={String(row[c.id] ?? '')} path={`${basePath}/${i}/${c.id}`} readonly={!editable} placeholder="1d6" />
                      <button class="small primary" onclick={() => rollCell(row, c)} disabled={!String(row[c.id] ?? '').trim()}>Roll</button>
                    </span>
                  {:else if c.type === 'select'}
                    <select value={row[c.id] ?? ''} disabled={!editable} use:presence={pres(`${basePath}/${i}/${c.id}`)} onchange={(e) => setCell(i, c.id, (e.target as HTMLSelectElement).value)}>
                      <option value=""></option>
                      {#each c.options as o}<option value={o}>{o}</option>{/each}
                    </select>
                  {:else}
                    <DebouncedText value={String(row[c.id] ?? '')} path={`${basePath}/${i}/${c.id}`} readonly={!editable} />
                  {/if}
                </td>
              {/each}
              {#if editable}<td><button class="ghost small danger" onclick={() => removeRow(i)} title="Remove row">✕</button></td>{/if}
            </tr>
          {/each}
        </tbody>
      </table>
    </div>
    {#if editable}<button class="small" onclick={addRow} style="margin-top:.4em">+ Row</button>{/if}
  {/if}
</Collapsible>

<style>
  .help { margin-bottom: .4em; }
  .opts { display: flex; flex-direction: column; gap: .25em; }
  .opt { display: flex; gap: .5em; align-items: baseline; padding: .25em .5em; border-radius: 6px; cursor: pointer; color: var(--fg); font-size: 1em; }
  .opt.sel { background: var(--accent-soft); }
  .opt.ro { cursor: default; }
  .opt input { margin: 0; position: relative; top: .1em; }
  .listlbl { min-width: 5em; }
  :global(input.dice) { width: 6em; }
  .opt :global(.pips) { margin-left: auto; }
</style>
