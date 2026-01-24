<script lang="ts">
	import { Role } from '$lib/recorder';
	import { listDevices as listRecordedDevices, setDeviceRoles } from '$lib/recorder';
	import { checkDeviceAvailability } from '$lib/recorder';
	import { getStatus } from '$lib/recorder';
	import type { User } from 'firebase/auth';
	import { onMount } from 'svelte';
	import Select from 'svelte-select';

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
				status: string;
				local: boolean;
		  }[]
		| null = $state(null);

	const load = async () => {
		const recorded_devices = await listRecordedDevices(user);
		const statuses = await Promise.all(
			recorded_devices.map(async (device) => {
				const status = await getStatus(user, device.name);
				return {
					...device,
					ui_allowed_roles: device.allowed_roles.map((role) => ({ value: role, label: role })),
					status: status.status
				};
			})
		);
		devices_with_locality = await Promise.all(
			statuses.map(async (device) => ({
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
				<form class="mt-4 flex flex-row items-center gap-4">
					<Select
						class="mt-4"
						items={Object.values(Role).map((role) => ({ value: role, label: role }))}
						bind:value={device.ui_allowed_roles}
						multiple
					/>
					<button
						type="button"
						class="rounded border px-4 py-2 hover:bg-gray-100 disabled:opacity-25"
						disabled={!device.ui_allowed_roles ||
							device.ui_allowed_roles.map((role) => role.value).toString() ===
								device.allowed_roles.toString()}
						onclick={() => {
							if (!device.ui_allowed_roles) return;
							setDeviceRoles(
								user,
								device.name,
								device.ui_allowed_roles.map((role) => role.value)
							);
							device.allowed_roles = device.ui_allowed_roles.map((role) => role.value);
						}}
						aria-label="Spara"
					>
						Spara
					</button>
				</form>
			</div>
		{/each}
	{/if}
</div>
