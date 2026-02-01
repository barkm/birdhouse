<script lang="ts">
	import { Role } from '$lib/recorder';
	import { listDevices as listRecordedDevices } from '$lib/recorder';
	import { checkDeviceAvailability } from '$lib/recorder';
	import type { User } from 'firebase/auth';
	import { onMount } from 'svelte';
	import DeviceCard from './DeviceCard.svelte';

	interface Props {
		user: User;
	}

	const { user }: Props = $props();

	let devices_with_locality:
		| {
				name: string;
				allowed_roles: Role[];
				ui_allowed_roles?: { value: Role; label: string }[];
				active: boolean;
				local: boolean;
		  }[]
		| null = $state(null);

	const load = async () => {
		const recorded_devices = await listRecordedDevices(user);
		devices_with_locality = await Promise.all(
			recorded_devices.map(async (device) => ({
				...device,
				local: await checkDeviceAvailability(device.name)
			}))
		);
	};

	onMount(load);
</script>

<div class="flex flex-col gap-4">
	{#if devices_with_locality === null}
		{#each Array(3) as _}
			<div class="animate-pulse rounded-lg bg-gray-100 p-4">
				<div class="h-6 w-1/3 rounded bg-gray-300"></div>
				<div class="mt-2 h-4 w-1/2 rounded bg-gray-300"></div>
			</div>
		{/each}
	{:else}
		{#each devices_with_locality as device}
			<DeviceCard
				{user}
				name={device.name}
				local={device.local}
				allowed_roles={device.allowed_roles}
				active={device.active}
			/>
		{/each}
	{/if}
</div>
