<script lang="ts">
	import { PUBLIC_RELAY_URL, PUBLIC_RECORDER_URL } from '$env/static/public';
	import VideoWithLoader from '$lib/VideoWithLoader.svelte';

	interface Device {
		name: string;
	}

	interface Playlist {
		path: string;
	}

	interface Recording {
		url: string;
		time: string;
	}

	const props: { device: Device } = $props();

	const fetch_device_playlists = async (
		device: Device
	): Promise<{ device: Device; playlist: Playlist }> => {
		const playlist_response = await fetch(`${PUBLIC_RELAY_URL}${device.name}/start?bitrate=500000`);
		const data = await playlist_response.json();
		return {
			device,
			playlist: {
				path: data.playlist
			}
		};
	};

	const fetch_recordings = async (device: Device): Promise<Recording[]> => {
		const recordings_response = await fetch(`${PUBLIC_RECORDER_URL}recordings/${device.name}`);
		return await recordings_response.json();
	};

	const device_playlist_promise = $derived(fetch_device_playlists(props.device));
	const recordings_promise = $derived(fetch_recordings(props.device));
	const sorted_recordings_promise = $derived(
		recordings_promise.then((recordings) =>
			recordings.sort((a, b) => a.time.localeCompare(b.time)).reverse()
		)
	);
</script>

<column>
	{#await device_playlist_promise then device_playlist}
		<stream>
			<VideoWithLoader
				src={`${PUBLIC_RELAY_URL}${device_playlist.device.name}${device_playlist.playlist.path}`}
				controls
				autoplay
				muted
				playsinline
			/>
		</stream>
	{/await}
	{#await sorted_recordings_promise then recordings}
		<recordings>
			{#each recordings as recording (recording.url)}
				<recording>
					<strong>{recording.time}</strong>
					<VideoWithLoader src={recording.url} autoplay muted playsinline loop />
				</recording>
			{/each}
		</recordings>
	{/await}
</column>

<style>
	column {
		display: flex;
		flex-direction: column;
		align-items: center;
		width: 100%;
		gap: 1rem;
		padding: 1rem;
		min-width: 300px;
		max-width: 1500px;
	}
	stream {
		width: 75%;
		min-width: 335px;
		align-items: center;
	}

	recordings {
		width: 90%;
		justify-items: center;
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
		gap: 1rem;
	}

	recording {
		display: flex;
		flex-direction: column;
		align-items: center;
		width: 100%;
		max-width: 500px;
	}
</style>
