<script lang="ts">
  import HLSPlayer from '$lib/HLSPlayer.svelte';
  import { PUBLIC_RELAY_URL } from '$env/static/public';
</script>

<HLSPlayer relay_url={PUBLIC_RELAY_URL} />
