<script lang="ts">
	import SensorCard from '$lib/components/SensorCard.svelte';
	import SensorLoader from '$lib/components/SensorLoader.svelte';
	import VideoWithLoader from '$lib/components/video/VideoWithLoader.svelte';
	import { getLocations, getCurrentSensorData, startAndGetStreamUrl } from '$lib/recorder';
	import type { User } from 'firebase/auth';

	interface Props {
		user: User;
	}

	const { user }: Props = $props();

	const capitalize = (s: string) => s.charAt(0).toUpperCase() + s.slice(1);

	const locations_promise = getLocations(user);

	const sensor_data_promise = locations_promise.then((locs) =>
		Promise.all(
			locs.map(async (loc) => {
				if (!loc.current_device_name) return { name: loc.name, data: null };
				try {
					const data = await getCurrentSensorData(user, loc.current_device_name);
					return { name: loc.name, data };
				} catch (error) {
					console.error(`Failed to load sensor data for ${loc.name}:`, error);
					return { name: loc.name, data: null };
				}
			})
		)
	);

	const streams_promise = locations_promise.then(async (locs) => {
		const id_token = await user.getIdToken();
		const results = await Promise.all(
			locs
				.filter((loc) => loc.current_device_name)
				.map(async (loc) => {
					try {
						const url = await startAndGetStreamUrl(user, loc.current_device_name!);
						return url ? { stream_url: url, id_token } : null;
					} catch (error) {
						console.error(`Failed to load stream for ${loc.name}:`, error);
						return null;
					}
				})
		);
		return results.filter((r): r is { stream_url: string; id_token: string } => r !== null);
	});
</script>

<div class="grid grid-cols-2 gap-4">
	{#await locations_promise then locs}
		{#await sensor_data_promise}
			{#each locs as _}
				<SensorLoader limits={false} />
			{/each}
		{:then location_sensors}
			{#each location_sensors as loc}
				{#if loc.data}
					<SensorCard
						title={capitalize(loc.name)}
						temperature={loc.data.temperature}
						humidity={loc.data.humidity}
					/>
				{/if}
			{/each}
		{/await}
	{/await}
</div>
{#await locations_promise then locs}
	{#await streams_promise}
		{#each locs.filter((l) => l.current_device_name) as _}
			<VideoWithLoader autoplay muted playsinline controls />
		{/each}
	{:then streams}
		{#each streams as stream}
			<VideoWithLoader id_token={stream.id_token} src={stream.stream_url} autoplay muted playsinline controls />
		{/each}
	{/await}
{/await}
