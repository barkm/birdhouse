<script lang="ts">
  import { onMount, onDestroy } from 'svelte';
  import Hls from 'hls.js';

  export let src: string;

  let videoElement: HTMLVideoElement;
  let hls: Hls | null = null;

  onMount(() => {
    if (Hls.isSupported()) {
      hls = new Hls();
      hls.loadSource(src);
      hls.attachMedia(videoElement);
    } else if (videoElement.canPlayType('application/vnd.apple.mpegurl')) {
      // Native HLS support (Safari)
      videoElement.src = src;
    }

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