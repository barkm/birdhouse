<script lang="ts">
  import { onMount, onDestroy } from 'svelte';
  import Hls from 'hls.js';

  const { relay_url } = $props<{ relay_url: string }>();

  let videoElement: HTMLVideoElement;
  let hls: Hls | null = null;

  const playlist_path_promise = $derived(
    fetch(`${relay_url}birdhouse/start`).then((res) => res.json()).then((data): string | undefined => data.playlist)
  )

  onMount(() => {
    playlist_path_promise.then((playlist_path?: string) => {
      if (!playlist_path) {
        console.log('No playlist found');
        return
      }
      if (Hls.isSupported()) {
        hls = new Hls();
        hls.loadSource(`${relay_url}birdhouse${playlist_path}`);
        hls.attachMedia(videoElement);
      } else if (videoElement.canPlayType('application/vnd.apple.mpegurl')) {
        videoElement.src = `${relay_url}birdhouse${playlist_path}`;
      }
    });

    return () => {
      if (hls) {
        hls.destroy();
        hls = null;
      }
    };
  });

  onDestroy(() => {
    if (hls) {
      hls.destroy();
      hls = null;
    }
  });
</script>


<video
  bind:this={videoElement}
  controls
  autoplay
  muted
  playsinline
  style="width: 100%; max-width: 800px;"
></video>