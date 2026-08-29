<script lang="ts">
	import SensorCard from '$lib/components/SensorCard.svelte';
	import SensorLoader from '$lib/components/SensorLoader.svelte';
	import VideoWithLoader from '$lib/components/video/VideoWithLoader.svelte';
	import { getLocations, getCurrentSensorData, startAndGetStreamUrl } from '$lib/recorder';
	import type { SensorData } from '$lib/recorder';
	import type { User } from 'firebase/auth';

	interface Props {
		user: User;
	}

	const { user }: Props = $props();

	const capitalize = (s: string) => s.charAt(0).toUpperCase() + s.slice(1);

	interface LocationView {
		name: string;
		sensor: Promise<SensorData | null>;
		stream: Promise<{ stream_url: string; id_token: string } | null>;
	}

	const locations_promise: Promise<LocationView[]> = getLocations(user).then((locs) =>
		locs
			.filter((loc) => loc.current_device_name)
			.map((loc) => ({
				name: loc.name,
				sensor: getCurrentSensorData(user, loc.current_device_name!).catch((error) => {
					console.error(`Failed to load sensor data for ${loc.name}:`, error);
					return null;
				}),
				stream: (async () => {
					try {
						const url = await startAndGetStreamUrl(user, loc.current_device_name!);
						if (!url) return null;
						return { stream_url: url, id_token: await user.getIdToken() };
					} catch (error) {
						console.error(`Failed to load stream for ${loc.name}:`, error);
						return null;
					}
				})()
			}))
	);
</script>

<div class="grid grid-cols-2 gap-4">
	{#await locations_promise then locations}
		{#each locations as loc}
			{#await loc.sensor}
				<SensorLoader limits={false} />
			{:then data}
				{#if data}
					<SensorCard
						title={capitalize(loc.name)}
						temperature={data.temperature}
						humidity={data.humidity}
					/>
				{/if}
			{/await}
		{/each}
	{/await}
</div>
{#await locations_promise then locations}
	{#each locations as loc}
		{#await loc.stream}
			<VideoWithLoader autoplay muted playsinline controls />
		{:then stream}
			{#if stream}
				<VideoWithLoader
					id_token={stream.id_token}
					src={stream.stream_url}
					autoplay
					muted
					playsinline
					controls
				/>
			{/if}
		{/await}
	{/each}
{/await}
