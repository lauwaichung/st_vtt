<script lang="ts">
  import type { CharacterDoc, Move, SharedDoc, TrackKind, TrackState } from '../../lib/types';
  import type { Patcher } from '../../lib/patch';
  import { openRoll } from '../../lib/dialogs.svelte';
  import { send } from '../../lib/ws';
  import Markdown from '../../ui/Markdown.svelte';
  import { renderInline } from '../../lib/markdown';
  import Tracks from '../../ui/Tracks.svelte';
  import MoveOptions from './MoveOptions.svelte';

  let {
    move, characterId = null, sharedId = null, editable = false, tracks, ontrack, onremove, compact = false, canRoll = true,
    doc, p,
  }: {
    move: Move; characterId?: string | null; sharedId?: string | null; editable?: boolean;
    tracks?: TrackState; ontrack?: (kind: TrackKind, v: number) => void;
    onremove?: () => void; compact?: boolean; canRoll?: boolean;
    /** the sheet this card sits on, when the move carries its own checklist */
    doc?: CharacterDoc | SharedDoc; p?: Patcher;
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
    {#if ontrack}
      <Tracks tracks={move.tracks} state={tracks} onchange={ontrack} disabled={!editable} />
    {/if}
    <button class="ghost small" title="Post this move to the chat" onclick={() => send({ type: 'share_move', character_id: characterId, move_id: move.id }).catch(() => {})}>Share</button>
    {#if move.roll && canRoll}
      <button class="small primary" onclick={() => openRoll({ characterId, sharedId, move })}>Roll</button>
    {/if}
    {#if onremove && editable}<button class="ghost small danger" onclick={onremove} title="Remove">✕</button>{/if}
  </div>
  {#if open}
    <div class="body">
      {#if move.trigger}<p class="muted"><em>{@html renderInline(move.trigger)}</em></p>{/if}
      {#if move.text}<Markdown text={move.text} />{/if}
      {#if Object.keys(move.outcomes).length}
        <dl class="outcomes">
          {#each Object.entries(move.outcomes) as [tier, outcome]}
            <dt>{tier}</dt><dd><Markdown text={outcome.text} /></dd>
          {/each}
        </dl>
      {/if}
      {#if move.options.length && doc && p}
        <MoveOptions {move} {doc} {p} {editable} />
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
