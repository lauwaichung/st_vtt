<script lang="ts">
  import { timeShort } from '../lib/util';
  import Markdown from '../ui/Markdown.svelte';
  import type { Message } from '../lib/types';

  let { message }: { message: Message } = $props();
  const p = $derived(message.payload);
</script>

<div class="mc">
  <div class="row top">
    <strong>{message.author}</strong>
    {#if p.character}<span class="muted small">as {p.character}</span>{/if}
    <span class="muted small">shared a move</span>
    <span class="grow"></span>
    <span class="muted small">{timeShort(message.ts)}</span>
  </div>
  <div class="name">{p.name}</div>
  {#if p.trigger}<p class="muted"><em>{p.trigger}</em></p>{/if}
  {#if p.text}<Markdown text={p.text} />{/if}
  {#if p.outcomes && Object.keys(p.outcomes).length}
    <dl class="outcomes">
      {#each Object.entries(p.outcomes) as [tier, text]}
        <dt>{tier}</dt><dd><Markdown text={String(text)} /></dd>
      {/each}
    </dl>
  {/if}
  {#if p.hold}<p class="small muted">Hold: <strong>{p.hold.name}</strong>{#if p.hold.note} — {p.hold.note}{/if}</p>{/if}
</div>

<style>
  .mc { border: 1px solid var(--border); border-left: 4px solid var(--accent); border-radius: 6px; padding: .4em .6em; background: var(--bg); }
  .top { gap: .4em; }
  .name { font-weight: 600; margin: .15em 0; }
  .outcomes { display: grid; grid-template-columns: auto 1fr; gap: .15em .6em; margin: .3em 0 0; }
  .outcomes dt { font-weight: 600; color: var(--fg-muted); font-variant-numeric: tabular-nums; }
  .outcomes dd { margin: 0; }
</style>
