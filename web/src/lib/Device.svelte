<script lang="ts">
	import { PUBLIC_RELAY_URL } from '$env/static/public';
	import VideoWithLoader from '$lib/VideoWithLoader.svelte';

	interface Device {
		name: string;
	}

	interface Playlist {
		path: string;
	}

	const props: { device: Device } = $props();

	const fetch_device_playlists = async (
		device: Device
	): Promise<{ device: Device; playlist: Playlist }> => {
		const playlist_response = await fetch(`${PUBLIC_RELAY_URL}${device.name}/start`);
		const data = await playlist_response.json();
		return {
			device,
			playlist: {
				path: data.playlist
			}
		};
	};

	const device_playlist_promise = $derived(fetch_device_playlists(props.device));
</script>

{#await device_playlist_promise then device_playlist}
<column>
	<stream>
		<VideoWithLoader
			src={`${PUBLIC_RELAY_URL}${device_playlist.device.name}${device_playlist.playlist.path}`}
		/>
	</stream>
</column>
{/await}

<style>
	column {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 1rem;
		padding: 1rem;
	}
	stream {
		width: 75%;
	}
</style>
