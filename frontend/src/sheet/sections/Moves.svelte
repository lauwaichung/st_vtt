<script lang="ts">
  import { app } from '../../lib/state.svelte';
  import { moveIndex, uid } from '../../lib/util';
  import type { CharacterDoc, Move, Playbook } from '../../lib/types';
  import type { Patcher } from '../../lib/patch';
  import Collapsible from '../../ui/Collapsible.svelte';
  import Stepper from '../../ui/Stepper.svelte';
  import MoveCard from './MoveCard.svelte';

  let { doc, p, editable, pb, characterId }: { doc: CharacterDoc; p: Patcher; editable: boolean; pb: Playbook | undefined; characterId: string } = $props();
  const content = $derived(app.content!);
  const index = $derived(moveIndex(content, doc, pb));
  const sharedIds = $derived(new Set(Object.values(content.moves).flat().map((m) => m.id)));
  const taken = $derived(doc.moves.taken.map((id) => index.get(id)).filter((m): m is Move => !!m && !sharedIds.has(m.id)));
  const available = $derived((pb?.moves ?? []).filter((m) => !doc.moves.taken.includes(m.id)));
  const startingCount = $derived((pb?.starting_moves.fixed.length ?? 0) + (pb?.starting_moves.choose.reduce((a, c) => a + c.n, 0) ?? 0));
  const expected = $derived(startingCount + (doc.level - content.pack.xp.start_level));
  const holdNames = $derived.by(() => {
    const names = new Set<string>([...content.pack.hold_names, ...(pb?.hold_names ?? [])]);
    for (const m of index.values()) if (m.hold) names.add(m.hold.name);
    for (const n of Object.keys(doc.moves.hold ?? {})) names.add(n);
    return [...names];
  });

  let picking = $state(false);
  let customOpen = $state(false);
  let cName = $state('');
  let cTrigger = $state('');
  let cText = $state('');
  let cStat = $state<string>('');

  function locked(m: Move): string | null {
    if (!m.requires) return null;
    const why: string[] = [];
    if (m.requires.level && doc.level < m.requires.level) why.push(`level ${m.requires.level}`);
    for (const r of m.requires.moves) if (!doc.moves.taken.includes(r)) why.push(index.get(r)?.name ?? r);
    return why.length ? `requires ${why.join(', ')}` : null;
  }
  function take(m: Move) {
    p('/moves/taken', m.id, 'list_add');
    if (m.replaces) p('/moves/taken', m.replaces, 'list_remove');
    picking = false;
  }
  function remove(id: string) {
    p('/moves/taken', id, 'list_remove');
  }
  function addCustom() {
    if (!cName.trim()) return;
    const m: Move = {
      id: `custom_${uid()}`, name: cName.trim(), trigger: cTrigger, text: cText,
      roll: cStat === '' ? null : { stat: cStat === 'nothing' ? null : cStat === 'choose' ? 'choose' : cStat, bonus: 0, label: null },
      outcomes: {}, hold: null, pips: null, requires: null, tags: ['custom'], replaces: null,
    };
    p('/custom_moves/-', m);
    p('/moves/taken', m.id, 'list_add');
    cName = cTrigger = cText = ''; cStat = ''; customOpen = false;
  }
</script>

<Collapsible id="moves.{characterId}" title="Moves" subtitle={editable && taken.length < expected ? `pick ${expected - taken.length} more` : ''}>
  {#snippet right()}
    {#if editable}
      <button class="small" onclick={() => (picking = !picking)}>{picking ? 'Close' : '+ Move'}</button>
      <button class="small" onclick={() => (customOpen = !customOpen)}>+ Custom</button>
    {/if}
  {/snippet}

  {#if picking}
    <div class="picker">
      {#if available.length === 0}<p class="muted">No more playbook moves.</p>{/if}
      {#each available as m}
        {@const why = locked(m)}
        <div class="row pick">
          <div class="grow">
            <strong>{m.name}</strong> {#if why}<span class="tag warn">{why}</span>{/if}
            {#if pb?.starting_moves.choose.some((c) => c.from.includes(m.id))}<span class="tag">starting option</span>{/if}
            <div class="muted small">{m.trigger || m.text.slice(0, 120)}</div>
          </div>
          <button class="small" onclick={() => take(m)}>Take</button>
        </div>
      {/each}
    </div>
  {/if}
  {#if customOpen}
    <div class="picker stack">
      <input type="text" placeholder="Move name" bind:value={cName} />
      <input type="text" placeholder="Trigger (optional)" bind:value={cTrigger} />
      <textarea placeholder="Text (markdown)" bind:value={cText} rows="3"></textarea>
      <div class="row">
        <select bind:value={cStat}>
          <option value="">no roll</option>
          <option value="nothing">roll +nothing</option>
          <option value="choose">roll + chosen stat</option>
          {#each content.pack.stats as s}<option value={s.id}>roll +{s.label}</option>{/each}
        </select>
        <button class="small primary" onclick={addCustom} disabled={!cName.trim()}>Add</button>
      </div>
    </div>
  {/if}

  {#each taken as m (m.id)}
    <MoveCard move={m} {characterId} {editable} pips={doc.moves.pips?.[m.id] ?? 0}
      onpips={m.pips ? (v) => p(`/moves/pips/${m.id}`, v) : undefined}
      onremove={() => remove(m.id)} />
  {/each}
  {#if taken.length === 0}<p class="muted small">No playbook moves yet.</p>{/if}

  {#if holdNames.length}
    <div class="row hold">
      <span class="muted small">Hold</span>
      {#each holdNames as h}
        <Stepper label={h} value={doc.moves.hold?.[h] ?? 0} min={0} onchange={(v) => p(`/moves/hold/${h}`, v)} path={`/moves/hold/${h}`} disabled={!editable} />
      {/each}
    </div>
  {/if}

  {#each Object.entries(content.moves) as [group, moves]}
    <Collapsible id="moves.{group}" title="{group} moves" open={false}>
      {#each moves as m (m.id)}
        <MoveCard move={m} {characterId} {editable} compact
          pips={doc.moves.pips?.[m.id] ?? 0} onpips={m.pips ? (v) => p(`/moves/pips/${m.id}`, v) : undefined} />
      {/each}
    </Collapsible>
  {/each}
</Collapsible>

<style>
  .picker { border: 1px dashed var(--border); border-radius: 6px; padding: .5em .75em; margin: .25em 0 .5em; }
  .pick { padding: .25em 0; border-bottom: 1px solid var(--border); }
  .pick:last-child { border-bottom: 0; }
  .tag.warn { color: var(--warn); }
  .hold { margin: .5em 0; gap: 1em; }
</style>
