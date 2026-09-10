<script lang="ts">
  import { app } from '../../lib/state.svelte';
  import { uid } from '../../lib/util';
  import type { CharacterDoc, GearItem } from '../../lib/types';
  import type { Patcher } from '../../lib/patch';
  import Collapsible from '../../ui/Collapsible.svelte';
  import DebouncedText from '../../ui/DebouncedText.svelte';
  import Pips from '../../ui/Pips.svelte';
  import Stepper from '../../ui/Stepper.svelte';

  let { doc, p, editable }: { doc: CharacterDoc; p: Patcher; editable: boolean } = $props();
  const content = $derived(app.content!);
  const items = $derived(doc.gear?.items ?? []);
  const load = $derived(items.reduce((a, i) => a + (Number(i.weight) || 0), 0));
  const loadLabel = $derived.by(() => {
    const r = content.pack.load;
    if (!r) return '';
    if (load <= r.light) return 'light';
    if (load <= r.normal) return 'normal';
    if (load <= r.heavy) return 'heavy';
    return 'overloaded';
  });

  function add() {
    const item: GearItem = { id: uid(), name: '', tags: [], weight: 1, uses: null, notes: '' };
    p('/gear/items/-', item);
  }
  function remove(i: number) {
    p(`/gear/items/${i}`, null, 'remove');
  }
  function setTags(i: number, text: string) {
    p(`/gear/items/${i}/tags`, text.split(',').map((t) => t.trim()).filter(Boolean));
  }
  function toggleUses(i: number, item: GearItem) {
    p(`/gear/items/${i}/uses`, item.uses ? null : { max: 3, used: 0 });
  }
</script>

<Collapsible id="gear.{doc.name}" title="Gear" subtitle={content.pack.load ? `load ${load} (${loadLabel})` : `load ${load}`}>
  {#snippet right()}
    {#if editable}<button class="small" onclick={add}>+ Item</button>{/if}
  {/snippet}
  {#if content.pack.gear_tags.length}
    <datalist id="gear-tags">{#each content.pack.gear_tags as t}<option value={t}></option>{/each}</datalist>
  {/if}
  <div style="overflow-x:auto">
    <table class="grid">
      <thead><tr><th>Item</th><th>Tags</th><th>Wt</th><th>Uses</th><th>Notes</th>{#if editable}<th></th>{/if}</tr></thead>
      <tbody>
        {#each items as item, i (item.id ?? i)}
          <tr>
            <td><DebouncedText value={item.name} path={`/gear/items/${i}/name`} readonly={!editable} placeholder="Item" /></td>
            <td><DebouncedText value={(item.tags ?? []).join(', ')} onchange={(v) => setTags(i, v)} readonly={!editable} placeholder="hand, close" /></td>
            <td><Stepper value={Number(item.weight) || 0} min={0} onchange={(v) => p(`/gear/items/${i}/weight`, v)} path={`/gear/items/${i}/weight`} disabled={!editable} /></td>
            <td>
              {#if item.uses}
                <span class="row" style="gap:.3em">
                  <Pips value={item.uses.used} max={item.uses.max} onchange={(v) => p(`/gear/items/${i}/uses/used`, v)} path={`/gear/items/${i}/uses/used`} disabled={!editable} />
                  {#if editable}
                    <Stepper value={item.uses.max} min={1} max={20} onchange={(v) => p(`/gear/items/${i}/uses/max`, v)} path={`/gear/items/${i}/uses/max`} />
                    <button class="ghost small" onclick={() => toggleUses(i, item)} title="No uses">✕</button>
                  {/if}
                </span>
              {:else if editable}
                <button class="ghost small" onclick={() => toggleUses(i, item)}>+ uses</button>
              {/if}
            </td>
            <td><DebouncedText value={item.notes ?? ''} path={`/gear/items/${i}/notes`} readonly={!editable} /></td>
            {#if editable}<td><button class="ghost small danger" onclick={() => remove(i)}>✕</button></td>{/if}
          </tr>
        {/each}
      </tbody>
    </table>
  </div>
  {#if items.length === 0}<p class="muted small">Nothing carried.</p>{/if}
</Collapsible>
