<script lang="ts">
  import HLSPlayer from '$lib/HLSPlayer.svelte';
  import { PUBLIC_API_URL } from '$env/static/public';
</script>

<HLSPlayer src={PUBLIC_API_URL} />
