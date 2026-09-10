<script lang="ts">
  import type { Move } from '../../lib/types';
  import { openRoll } from '../../lib/dialogs.svelte';
  import { send } from '../../lib/ws';
  import Markdown from '../../ui/Markdown.svelte';
  import Pips from '../../ui/Pips.svelte';

  let {
    move, characterId = null, editable = false, pips = 0, onpips, onremove, compact = false, canRoll = true,
  }: {
    move: Move; characterId?: string | null; editable?: boolean; pips?: number;
    onpips?: (v: number) => void; onremove?: () => void; compact?: boolean; canRoll?: boolean;
  } = $props();
  // svelte-ignore state_referenced_locally
  let open = $state(!compact);
</script>

<div class="move" class:compact>
  <div class="row head">
    <button class="ghost name" onclick={() => (open = !open)}>{move.name}</button>
    {#each move.tags as t}<span class="tag">{t}</span>{/each}
    {#if move.requires?.level}<span class="tag">lvl {move.requires.level}+</span>{/if}
    <span class="grow"></span>
    {#if move.pips && onpips}
      <Pips value={pips} max={move.pips} onchange={onpips} disabled={!editable} />
    {/if}
    <button class="ghost small" title="Post this move to the chat" onclick={() => send({ type: 'share_move', character_id: characterId, move_id: move.id }).catch(() => {})}>Share</button>
    {#if move.roll && canRoll}
      <button class="small primary" onclick={() => openRoll({ characterId, move })}>Roll</button>
    {/if}
    {#if onremove && editable}<button class="ghost small danger" onclick={onremove} title="Remove">✕</button>{/if}
  </div>
  {#if open}
    <div class="body">
      {#if move.trigger}<p class="muted"><em>{move.trigger}</em></p>{/if}
      {#if move.text}<Markdown text={move.text} />{/if}
      {#if Object.keys(move.outcomes).length}
        <dl class="outcomes">
          {#each Object.entries(move.outcomes) as [tier, text]}
            <dt>{tier}</dt><dd><Markdown {text} /></dd>
          {/each}
        </dl>
      {/if}
      {#if move.hold}<p class="small muted">Hold: <strong>{move.hold.name}</strong>{#if move.hold.note} — {move.hold.note}{/if}</p>{/if}
    </div>
  {/if}
</div>

<style>
  .move { border: 1px solid var(--border); border-radius: 6px; padding: .3em .6em; margin: .3em 0; background: var(--bg); }
  .head { gap: .35em; }
  .name { font-weight: 600; padding: .1em .2em; color: var(--fg); text-align: left; }
  .body { padding: .2em 0 .3em; }
  .outcomes { display: grid; grid-template-columns: auto 1fr; gap: .15em .6em; margin: .3em 0 0; }
  .outcomes dt { font-weight: 600; color: var(--fg-muted); font-variant-numeric: tabular-nums; }
  .outcomes dd { margin: 0; }
</style>
