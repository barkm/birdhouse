<script lang="ts">
  import Hls from 'hls.js';
	import type { HTMLVideoAttributes } from 'svelte/elements';

  type Props = { src: string } & HTMLVideoAttributes;

  const { src, ...rest }: Props = $props();

  let videoElement: HTMLVideoElement;
  let hls: Hls | null = null;

  $effect(() => {
    if (!videoElement) {
      return
    }
    if (Hls.isSupported()) {
      hls = new Hls();
      hls.loadSource(src);
      hls.attachMedia(videoElement);
    } else if (videoElement.canPlayType('application/vnd.apple.mpegurl')) {
      videoElement.src = src;
    }
    return () => {
      if (hls) {
        hls.destroy();
        hls = null;
      }
    };
  });
</script>

<video bind:this={videoElement} {...rest}></video>
