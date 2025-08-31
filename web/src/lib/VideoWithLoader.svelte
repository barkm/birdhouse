<script lang="ts">
    import Video from '$lib/Video.svelte';
    let isLoading = $state(true);

    let props: { src: string } = $props();
</script>

<stream class:loading={isLoading}>
    <Video 
    src={props.src}
    controls
    autoplay
    muted
    playsinline
    onplaying={() => {
    isLoading = false;
    }}
    />
</stream>

<style>
  stream {
    width: 100%;
    aspect-ratio: 16 / 9;
    transition: opacity 1000ms ease-in-out;
  }

  stream.loading {
    opacity: 0.0;
  }

  stream :global(video) {
    width: 100%;
    height: 100%;
  }

</style>