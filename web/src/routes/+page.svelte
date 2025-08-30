<script lang="ts">
  import HLSPlayer from '$lib/HLSPlayer.svelte';
  import { PUBLIC_RELAY_URL } from '$env/static/public';
  
  const playlist_path_promise = $derived(
    fetch(`${PUBLIC_RELAY_URL}birdhouse/start`).then((res) => res.json()).then((data): string => data.playlist)
  )
</script>

{#await playlist_path_promise then playlist_path}
  <HLSPlayer src={`${PUBLIC_RELAY_URL}birdhouse${playlist_path}`} />
{/await}
