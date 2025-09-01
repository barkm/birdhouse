<script lang="ts">
	import Video from '$lib/Video.svelte';
	import { fade } from 'svelte/transition';
	import Loader from './Loader.svelte';
	let isLoading = $state(true);
	let props: { src: string } = $props();
</script>

<stream-with-loader>
	{#if isLoading}
		<loader transition:fade|global={{ duration: 500 }}>
			<Loader />
		</loader>
	{/if}
	<stream class:loading={isLoading}>
		<Video
			src={props.src}
			controls
			autoplay
			muted
			playsinline
			onplaying={() => {
				setTimeout(() => {
					isLoading = false;
				}, 4000);
			}}
		/>
	</stream>
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
