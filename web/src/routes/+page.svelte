<script lang="ts">
	import { PUBLIC_RELAY_URL } from '$env/static/public';
	import Device from '$lib/components/Device.svelte';
	import { authorizedRequest } from '$lib/request';
	import TemperatureChart from '$lib/components/TemperatureChart.svelte';
	import { user } from '$lib/firebase';

	interface Device {
		name: string;
	}

	const fetch_devices = async (): Promise<Device[]> => {
		const device_response = await authorizedRequest($user!, PUBLIC_RELAY_URL, 'list');
		return await device_response.json();
	};

	const getTemperature = async (device_name: string): Promise<number | null> => {
		const sensor_response = await authorizedRequest($user!, PUBLIC_RELAY_URL, `${device_name}/sensor`);
		return (await sensor_response.json())['temperature'];
	};

	const devices_promise = $derived(fetch_devices());
</script>

<column style="width: 100%">
	{#await devices_promise then devices}
		<devices>
			{#each devices as device (device.name)}
				{#if device.name.includes("house")}
					{#await getTemperature(device.name) then temperature}
					<div>
						{ device.name === "house" ? "Inomhus" : "Utomhus" }temperatur: {temperature !== null ? temperature.toFixed(1) : 'N/A'}°C
					</div>
					{/await}
				{/if}
			{/each}
			<br />
			<TemperatureChart {devices} />
			{#each devices as device (device.name)}
				{#if device.name === "birdhouse"}
					<Device {device} />
				{/if}
			{/each}
		</devices>
	{/await}
</column>

<style>
	devices {
		width: 100%;
		display: flex;
		flex-direction: column;
		align-items: center;
	}

	row {
		width: 100%;
		height: 100vh;
		display: flex;
		justify-content: center;
		align-items: center;
	}

	column {
		min-width: 300px;
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 5rem;
	}

	button {
		padding: 0.5rem 1rem;
		font-size: 1.2rem;
		background-color: white;
		color: black;
		border: 1px solid black;
		border-radius: none;
		cursor: pointer;
	}

	button:hover {
		background-color: black;
		color: white;
	}
</style>
