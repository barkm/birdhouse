<script lang="ts">
	import type { ComponentProps } from 'svelte';
	import VideoWithLoader from './VideoWithLoader.svelte';

	const { ...rest }: ComponentProps<typeof VideoWithLoader> = $props();

	let container: HTMLElement;

	// The video element is created only once the clip has been scrolled into
	// view. A grid of recordings would otherwise mount every clip at once, and
	// the browser fetches metadata for each one as it is mounted.
	let seen = $state(false);

	$effect(() => {
		const observer = new IntersectionObserver(([entry]) => {
			seen ||= entry.isIntersecting;
			const video = container.querySelector('video');
			// On the first intersection the element has not rendered yet, and
			// `autoplay` starts the clip instead.
			if (!video) return;
			if (entry.isIntersecting) {
				video.play();
			} else {
				video.pause();
			}
		});
		observer.observe(container);
		return () => observer.disconnect();
	});
</script>

<!-- The placeholder keeps the clip's space. A zero-height box would sit within
	 the viewport along with every other one and be reported as visible. -->
<div bind:this={container} class="aspect-video">
	{#if seen}
		<VideoWithLoader autoplay {...rest} />
	{/if}
</div>
