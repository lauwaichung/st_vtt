<script lang="ts">
  import { timeShort, fmtMod } from '../lib/util';
  import Markdown from '../ui/Markdown.svelte';
  import type { Message } from '../lib/types';

  let { message }: { message: Message } = $props();
  const p = $derived(message.payload);
  const tierClass = $derived(p.tier === '10+' ? 'hit' : p.tier === '7-9' ? 'mixed' : p.tier ? 'miss' : '');
</script>

<div class="rc {tierClass}">
  <div class="row top">
    <strong>{message.author}</strong>
    {#if p.character}<span class="muted small">as {p.character}</span>{/if}
    <span class="grow"></span>
    {#if p.gm_only}<span class="tag">GM only</span>{/if}
    <span class="muted small">{timeShort(message.ts)}</span>
  </div>
  <div class="row main">
    <span class="label">{p.label}</span>
    <span class="grow"></span>
    <span class="total">{p.total}</span>
    {#if p.tier}<span class="tier">{p.tier}</span>{/if}
  </div>
  <div class="detail muted small">
    {#each p.roll.dice as d, i}
      {#if i > 0 || d.sign < 0}<span>{d.sign < 0 ? '−' : '+'}</span>{/if}
      <span class="die" title={d.die}>{d.die}: [{d.results.map((r: number) => (d.kept.includes(r) ? r : `~${r}~`)).join(' ')}]</span>
    {/each}
    {#if p.roll.modifier}<span>{fmtMod(p.roll.modifier)}</span>{/if}
    {#if p.stat_label}<span>{fmtMod(p.stat_mod)} {p.stat_label}</span>{/if}
    {#if p.bonus}<span>{fmtMod(p.bonus)} bonus</span>{/if}
    {#if p.mode && p.mode !== 'normal'}<span class="pill">{p.mode === 'both' ? 'adv + disadv' : p.mode}</span>{/if}
    {#if p.auto_disadvantage?.length}<span class="pill warn">{p.auto_disadvantage.join(', ')}</span>{/if}
  </div>
  {#if p.outcome}
    <Markdown text={p.outcome} class="outcome" />
  {/if}
  {#if p.mark_xp}<span class="small xp">Mark XP</span>{/if}
</div>

<style>
  .rc { border: 1px solid var(--border); border-left: 4px solid var(--border); border-radius: 6px; padding: .4em .6em; background: var(--bg); }
  .rc.hit { border-left-color: var(--ok); }
  .rc.mixed { border-left-color: var(--warn); }
  .rc.miss { border-left-color: var(--bad); }
  .top { gap: .4em; }
  .main { gap: .5em; margin: .15em 0; }
  .label { font-weight: 600; }
  .total { font-size: 1.4em; font-weight: 700; font-variant-numeric: tabular-nums; }
  .tier { font-weight: 600; padding: 0 .5em; border-radius: 999px; background: var(--bg-sunken); }
  .hit .tier { color: var(--ok); } .mixed .tier { color: var(--warn); } .miss .tier { color: var(--bad); }
  .detail { display: flex; gap: .4em; flex-wrap: wrap; font-family: var(--mono); }
  .pill.warn { color: var(--warn); border-color: var(--warn); }
  .xp { color: var(--accent); font-weight: 600; }
  :global(.rc .outcome) { margin-top: .3em; padding-top: .3em; border-top: 1px dashed var(--border); }
</style>
