<script lang="ts">
  import HLSPlayer from '$lib/HLSPlayer.svelte';
  const streamUrl: string = 'http://localhost:8002/birdhouse/hls/playlist.m3u8';
</script>

<HLSPlayer src={streamUrl} />
