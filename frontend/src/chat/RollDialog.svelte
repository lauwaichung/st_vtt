<script lang="ts">
  import Modal from '../ui/Modal.svelte';
  import { app, isGm, myCharacters } from '../lib/state.svelte';
  import { send } from '../lib/ws';
  import { fmtMod } from '../lib/util';
  import type { RollRequest } from '../lib/dialogs.svelte';

  let { req, onclose }: { req: RollRequest; onclose: () => void } = $props();

  const content = $derived(app.content!);
  const candidates = $derived(isGm() ? Object.values(app.characters) : myCharacters());
  let characterId = $state(req.characterId ?? null);
  const doc = $derived(characterId ? app.characters[characterId]?.data : undefined);

  const spec = $derived(req.move?.roll ?? null);
  const statChoices = $derived.by((): string[] => {
    if (req.stat !== undefined && req.stat !== null) return [req.stat];
    if (!spec) return req.stat === null ? [] : content.pack.stats.map((s) => s.id);
    if (spec.stat === null) return [];
    if (spec.stat === 'choose') return content.pack.stats.map((s) => s.id);
    return Array.isArray(spec.stat) ? spec.stat : [spec.stat];
  });
  let stat = $state<string | null>(null);
  $effect(() => { if (stat === null || !statChoices.includes(stat)) stat = statChoices[0] ?? null; });

  let adv = $state(false);
  let disadv = $state(false);
  let bonus = $state(req.bonus ?? 0);
  let gmOnly = $state(false);

  const autoDis = $derived(
    doc && stat ? content.pack.debilities.filter((d) => doc.debilities?.[d.id] && d.affects.includes(stat!)).map((d) => d.label) : [],
  );
  const statMod = $derived(doc && stat ? doc.stats?.[stat] ?? 0 : 0);
  const label = $derived(req.label ?? req.move?.name ?? 'Roll');

  async function go() {
    await send({
      type: 'roll', character_id: characterId, move_id: req.move?.id ?? null, stat,
      advantage: adv, disadvantage: disadv, bonus, label, gm_only: gmOnly,
    }).catch(() => {});
    onclose();
  }
</script>

<Modal title={label} {onclose}>
  <div class="stack">
    {#if req.move?.trigger}<p class="muted"><em>{req.move.trigger}</em></p>{/if}
    {#if candidates.length > 1}
      <label>Character
        <select bind:value={characterId}>
          {#each candidates as c}<option value={c.id}>{c.data.name || '(unnamed)'}</option>{/each}
        </select>
      </label>
    {/if}
    {#if statChoices.length > 1}
      <div class="row">
        <span class="muted small">Stat</span>
        {#each statChoices as s}
          {@const def = content.pack.stats.find((x) => x.id === s)}
          <button class="small" class:primary={stat === s} onclick={() => (stat = s)}>{def?.label ?? s} {fmtMod(doc?.stats?.[s] ?? 0)}</button>
        {/each}
      </div>
    {:else if statChoices.length === 1}
      <div class="muted">Rolling {content.pack.roll.base} {fmtMod(statMod)} {content.pack.stats.find((x) => x.id === stat)?.label}</div>
    {:else}
      <div class="muted">Rolling {content.pack.roll.base} + nothing</div>
    {/if}
    {#if autoDis.length}
      <div class="warn">Disadvantage from {autoDis.join(', ')}</div>
    {/if}
    <div class="row">
      <label><input type="checkbox" bind:checked={adv} /> advantage</label>
      <label><input type="checkbox" bind:checked={disadv} /> disadvantage</label>
      <label>bonus <input type="number" bind:value={bonus} /></label>
      <label><input type="checkbox" bind:checked={gmOnly} /> GM only</label>
    </div>
    <div class="row" style="justify-content:flex-end">
      {#if req.move}
        <button class="ghost" onclick={() => { send({ type: 'share_move', character_id: characterId, move_id: req.move!.id }).catch(() => {}); }}>Share text</button>
      {/if}
      <span class="grow"></span>
      <button onclick={onclose}>Cancel</button>
      <button class="primary" onclick={go}>Roll</button>
    </div>
  </div>
</Modal>

<style>
  .warn { color: var(--warn); }
  label { display: inline-flex; gap: .3em; align-items: center; color: var(--fg); }
</style>
