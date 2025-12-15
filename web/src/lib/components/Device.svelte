<script lang="ts">
	import { PUBLIC_RECORDER_URL, PUBLIC_RELAY_URL } from '$env/static/public';
	import VideoWithLoader from '$lib/components/video/VideoWithLoader.svelte';
	import { user } from '$lib/firebase';
	import RecordButton from '$lib/components/record-button/RecordButton.svelte';
	import { authorizedRequest } from '$lib/request';

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
		if (!$user) {
			throw new Error('User not authenticated');
		}
		const playlist_response = await authorizedRequest(
			$user,
			PUBLIC_RELAY_URL,
			`${device.name}/start?bitrate=500000&framerate=24`
		);
		const data = await playlist_response.json();
		return {
			device,
			playlist: {
				path: data.playlist
			}
		};
	};

	const fetch_recordings = async (device: Device): Promise<Recording[]> => {
		if (!$user) {
			return [];
		}
		const recordings_response = await authorizedRequest(
			$user,
			PUBLIC_RECORDER_URL,
			`recordings/${device.name}`
		);
		return await recordings_response.json();
	};

	let device_playlist = $state<{ device: Device; playlist: Playlist } | null>(null);
	let video_stream: HTMLVideoElement | null = $state(null);

	$effect(() => {
		fetch_device_playlists(props.device).then((playlist) => {
			device_playlist = playlist;
		});
	});

	const recordings_promise = $derived(fetch_recordings(props.device));
	const sorted_recordings_promise = $derived(
		recordings_promise.then((recordings) =>
			recordings.sort((a, b) => a.time.localeCompare(b.time)).reverse()
		)
	);
</script>

<column>
	{#if $user}
		{#await $user.getIdToken() then id_token}
			<row>
				<fill></fill>
				<stream>
					<VideoWithLoader
						{id_token}
						src={device_playlist
							? `${PUBLIC_RELAY_URL}${device_playlist.device.name}${device_playlist.playlist.path}`
							: null}
						onplaying={(event: any) => {
							video_stream = event.currentTarget;
						}}
						controls
						autoplay
						muted
						playsinline
					/>
				</stream>
				<fill>
					<RecordButton video={video_stream} />
				</fill>
			</row>
		{/await}
	{/if}
	{#await sorted_recordings_promise then recordings}
		<recordings>
			{#each recordings.filter((_, i) => i % 7 === 0).slice(0, 12) as recording (recording.url)}
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

	row {
		display: flex;
		flex-direction: row;
		justify-content: center;
		width: 100%;
		height: 100%;
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

	fill {
		width: 50px;
	}
</style>
