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
			locs.map(async (loc) => ({
				name: loc.name,
				data: loc.current_device_name
					? await getCurrentSensorData(user, loc.current_device_name)
					: null
			}))
		)
	);

	const streams_promise = locations_promise.then(async (locs) => {
		const id_token = await user.getIdToken();
		const results = await Promise.all(
			locs
				.filter((loc) => loc.current_device_name)
				.map(async (loc) => {
					const url = await startAndGetStreamUrl(user, loc.current_device_name!);
					return url ? { stream_url: url, id_token } : null;
				})
		);
		return results.filter((r): r is { stream_url: string; id_token: string } => r !== null);
	});
</script>

<div class="grid grid-cols-2 gap-4">
	{#await sensor_data_promise}
		<SensorLoader limits={false} />
		<SensorLoader limits={false} />
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
</div>
{#await streams_promise then streams}
	{#each streams as stream}
		<VideoWithLoader id_token={stream.id_token} src={stream.stream_url} autoplay muted playsinline controls />
	{/each}
{/await}
