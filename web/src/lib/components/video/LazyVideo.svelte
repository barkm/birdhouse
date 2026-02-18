<script lang="ts">
	import type { ComponentProps } from 'svelte';
	import VideoWithLoader from './VideoWithLoader.svelte';

	const { ...rest }: ComponentProps<typeof VideoWithLoader> = $props();

	let container: HTMLElement;

	$effect(() => {
		const observer = new IntersectionObserver(([entry]) => {
			const video = container.querySelector('video');
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

<div bind:this={container}>
	<VideoWithLoader {...rest} />
</div>