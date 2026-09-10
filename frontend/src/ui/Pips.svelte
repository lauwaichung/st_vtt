<script lang="ts">
  import { getContext } from 'svelte';
  import { SHEET, type SheetContext } from '../lib/patch';
  import { presence } from '../lib/presence.svelte';

  let { value, max, onchange, disabled = false, path }: { value: number; max: number; onchange: (v: number) => void; disabled?: boolean; path?: string } = $props();
  const sheet = getContext<SheetContext | undefined>(SHEET);
  const pres = $derived(path && sheet ? { entity: sheet.entity, id: sheet.id, path } : undefined);
  function click(i: number) {
    onchange(value === i + 1 ? i : i + 1);
  }
</script>

<span class="pips" title="{value}/{max}" use:presence={pres} tabindex="-1">
  {#each Array(max) as _, i}
    <button class="pip" class:on={i < value} onclick={() => click(i)} {disabled} aria-label="pip {i + 1}"></button>
  {/each}
</span>
