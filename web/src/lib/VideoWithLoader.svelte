<script lang="ts">
	import type { ComponentProps } from 'svelte';
	import { fade } from 'svelte/transition';

	import Video from '$lib/Video.svelte';
	import Loader from './Loader.svelte';

	const { src, ...rest }: ComponentProps<typeof Video> = $props();

	let isLoading = $state(true);
</script>

<stream-with-loader>
	{#if isLoading || !src}
		<loader transition:fade|global={{ duration: 500 }}>
			<Loader />
		</loader>
	{/if}
	{#if src}
		<stream class:loading={isLoading}>
			<Video
				{src}
				{...rest}
				onplaying={() => {
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

	loader {
		position: absolute;
		width: 50%;
		transform: translate(50%, 50%);
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
