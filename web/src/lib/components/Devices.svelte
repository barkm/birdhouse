<script lang="ts">
	import { listDevices as listRecordedDevices } from '$lib/recorder';
	import { checkDeviceAvailability } from "$lib/recorder";
	import { getStatus } from '$lib/recorder';
	import type { User } from 'firebase/auth';

	interface Props {
		user: User;
	}

	const { user }: Props = $props();

	const recorded_devices_promise = $derived(listRecordedDevices(user));
	const statuses_promise = $derived(
		recorded_devices_promise.then((active) => {
			return Promise.all(
				active.map((device) =>
					getStatus(user, device.name).then((status) => ({
						name: device.name,
						active: device.active,
						status: status.status
					}))
				)
			);
		})
	);

	const devices_with_locality_promise = $derived(
		statuses_promise.then((devices) => {
			return Promise.all(
				devices.map(async (device) => ({
					...device,
					local: await checkDeviceAvailability(device.name)
				}))
			);
		})
	);
</script>

<div class="flex flex-col gap-4">
	{#await devices_with_locality_promise}
		{#each Array(3) as _}
			<div class="animate-pulse rounded-lg bg-gray-100 p-4">
				<div class="h-6 w-1/3 rounded bg-gray-300"></div>
				<div class="mt-2 h-4 w-1/2 rounded bg-gray-300"></div>
			</div>
		{/each}
	{:then devices}
		{#each devices as device}
			<div class="rounded-lg border border-gray-300 p-4">
				<div class="flex items-center justify-between">
					<div class="text-xl font-semibold">{device.name}</div>
					{#if device.active}
						<div class="rounded bg-green-100 px-2 py-1 text-sm font-medium text-green-800">
							Aktiv {device.local ? '(Lokal)' : '(Fjärr)'}
						</div>
					{:else}
						<div class="rounded bg-gray-100 px-2 py-1 text-sm font-medium text-gray-800">
							Inaktiv {device.local ? '(Lokal)' : '(Fjärr)'}
						</div>
					{/if}
				</div>
				{#if device.active}
					<div class="mt-2 text-gray-600">Status: {device.status ?? 'Okänd'}</div>
				{/if}
			</div>
		{/each}
	{/await}
</div>
