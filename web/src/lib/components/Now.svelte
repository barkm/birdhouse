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

	const sensor_data_promise = getLocations(user).then((locs) =>
		Promise.all(
			locs.map(async (loc) => ({
				name: loc.name,
				data: loc.current_device_name
					? await getCurrentSensorData(user, loc.current_device_name)
					: null
			}))
		)
	);

	let stream_url: string | undefined = $state(undefined);
	let id_token: string | undefined = $state(undefined);

	$effect(() => {
		getLocations(user).then(async (locs) => {
			for (const loc of locs) {
				if (!loc.current_device_name) continue;
				const [url, token] = await Promise.all([
					startAndGetStreamUrl(user, loc.current_device_name),
					user.getIdToken()
				]);
				if (url) {
					stream_url = url;
					id_token = token;
					break;
				}
			}
		});
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
<VideoWithLoader {id_token} src={stream_url} autoplay muted playsinline controls />
