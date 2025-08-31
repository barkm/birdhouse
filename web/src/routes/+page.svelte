<script lang="ts">
	import { PUBLIC_RELAY_URL } from '$env/static/public';
	import Device from '$lib/Device.svelte';
	import VideoWithLoader from '$lib/VideoWithLoader.svelte';

	interface Device {
		name: string;
	}

	interface Playlist {
		path: string;
	}

	const fetch_devices = async (): Promise<Device[]> => {
		const device_response = await fetch(`${PUBLIC_RELAY_URL}list`);
		return await device_response.json();
	};

	const devices_promise = fetch_devices();
</script>

{#await devices_promise then devices}
	{#each devices as device (device.name)}
		<Device {device} />
	{/each}
{/await}
