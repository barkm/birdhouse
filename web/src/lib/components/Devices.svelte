<script lang="ts">
	import { listDevices as listRecordedDevices } from '$lib/recorder';
	import { checkDeviceAvailability, getStatus, listDevices as listActiveDevices } from '$lib/relay';
	import type { User } from 'firebase/auth';

	interface Props {
		user: User;
	}

	const { user }: Props = $props();

	const recorded_devices_promise = $derived(listRecordedDevices(user));
	const active_devices_promise = $derived(listActiveDevices(user));
	const statuses_promise = $derived(
		active_devices_promise.then((active) => {
			return Promise.all(
				active.map((device) =>
					getStatus(user, device.name).then((status) => ({
						name: device.name,
						status: status.status
					}))
				)
			);
		})
	);

	const devices_promise = $derived(
		Promise.all([recorded_devices_promise, statuses_promise]).then(([recorded, active]) => {
			const active_set = new Set(active.map((device) => device.name));
			const recorded_set = new Set(recorded.map((device) => device.name));
			const all_devices = new Set([...active_set, ...recorded_set]);
			return [...all_devices].map((device) => ({
				name: device,
				is_active: active_set.has(device),
				status: active.find((d) => d.name === device)?.status
			}));
		})
	);

	const devices_with_locality_promise = $derived(
		devices_promise.then((devices) => {
			return Promise.all(
				devices.map(async (device) => ({
					...device,
					local: await checkDeviceAvailability(device.name)
				}))
			);
		})
	);
</script>

{#await devices_with_locality_promise then devices}
	<div class="flex flex-col gap-4">
		{#each devices as device}
			<div class="rounded-lg border border-gray-300 p-4">
				<div class="flex items-center justify-between">
					<div class="text-xl font-semibold">{device.name}</div>
					{#if device.is_active}
						<div class="rounded bg-green-100 px-2 py-1 text-sm font-medium text-green-800">
							Aktiv {device.local ? '(Lokal)' : '(Fjärr)'}
						</div>
					{:else}
						<div class="rounded bg-gray-100 px-2 py-1 text-sm font-medium text-gray-800">
							Inaktiv {device.local ? '(Lokal)' : '(Fjärr)'}
						</div>
					{/if}
				</div>
				{#if device.is_active}
					<div class="mt-2 text-gray-600">Status: {device.status ?? 'Okänd'}</div>
				{/if}
			</div>
		{/each}
	</div>
{/await}
