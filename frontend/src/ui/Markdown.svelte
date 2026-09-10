<script lang="ts">
  import { render } from '../lib/markdown';
  let { text, class: klass = '' }: { text: string | null | undefined; class?: string } = $props();
</script>

<div class="md {klass}">{@html render(text)}</div>
