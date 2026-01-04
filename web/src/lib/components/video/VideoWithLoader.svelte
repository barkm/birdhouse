<script lang="ts">
	import type { ComponentProps } from 'svelte';
	import { fade } from 'svelte/transition';

	import Video from './Video.svelte';
	import Loader from '$lib/components/loader/Loader.svelte';

	const { src, onplaying, oncanplay, ...rest }: ComponentProps<typeof Video> = $props();

	let isLoading = $state(true);
</script>

<stream-with-loader >
	{#if isLoading || !src}
		<div class="h-full" transition:fade|global={{ duration: 500 }}>
			<Loader />
		</div>
	{/if}
	{#if src}
		<stream class:loading={isLoading} class="overflow-hidden rounded-lg">
			<Video
				{src}
				{...rest}
				onplaying={(event: any) => {
					onplaying?.(event);
					isLoading = false;
				}}
				oncanplay={(event: any) => {
					oncanplay?.(event);
					isLoading = false;
				}}
			/>
		</stream>
	{/if}
</stream-with-loader>

<style>
	stream-with-loader {
		width: 100%;
		aspect-ratio: 16 / 9;
		display: block;
		position: relative;
	}

	stream {
		width: 100%;
		transition: opacity 500ms ease-in-out;
		transition-delay: 500ms;
		position: absolute;
	}

	stream.loading {
		opacity: 0;
	}

	stream :global(video) {
		width: 100%;
		height: 100%;
	}
</style>
