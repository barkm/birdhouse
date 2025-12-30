<script lang="ts">
	import SensorCard from '$lib/components/SensorCard.svelte';
	import SensorLoader from '$lib/components/SensorLoader.svelte';
	import VideoWithLoader from '$lib/components/video/VideoWithLoader.svelte';
	import { getSensorData, startAndGetStreamUrl } from '$lib/relay';
	import type { User } from 'firebase/auth';

	interface Props {
		user: User;
	}

	const { user }: Props = $props();

	const inside_sensor_data_promise = getSensorData(user, 'house');
	const outside_sensor_data_promise = getSensorData(user, 'birdhouse');

	let stream_url: string | undefined = $state(undefined);
	let id_token: string | undefined = $state(undefined);

	$effect(() => {
		const url_promise = startAndGetStreamUrl(user, 'birdhouse');
		const id_token_promise = user.getIdToken();
		Promise.all([url_promise, id_token_promise]).then(([url, token]) => {
			stream_url = url;
			id_token = token;
		});
	});
</script>

<div class="mx-auto max-w-4xl p-6">
	<div class="space-y-4">
		<div class="grid grid-cols-2 gap-4">
			{#await outside_sensor_data_promise}
				<SensorLoader />
			{:then outsideSensorData}
				<SensorCard
					title={'Utomhus'}
					temperature={outsideSensorData.temperature}
					humidity={outsideSensorData.humidity}
				/>
			{/await}
			{#await inside_sensor_data_promise}
				<SensorLoader />
			{:then insideSensorData}
				<SensorCard
					title={'Inomhus'}
					temperature={insideSensorData.temperature}
					humidity={insideSensorData.humidity}
				/>
			{/await}
		</div>
		<div class="overflow-hidden rounded-lg">
			<VideoWithLoader {id_token} src={stream_url} autoplay muted playsinline controls />
		</div>
	</div>
</div>
