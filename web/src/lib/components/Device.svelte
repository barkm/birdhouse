<script lang="ts">
	import type { User } from 'firebase/auth';
	import RecordingsGrid from './RecordingsGrid.svelte';
	import { getDevice, Role, setDeviceRoles } from '$lib/recorder';
	import { onMount } from 'svelte';
	import Select from 'svelte-select';

	interface Props {
		user: User;
		name: string;
	}

	const { user, name }: Props = $props();

	let allowed_roles: string[] = $state([]);
	let ui_allowed_roles: { value: Role; label: string }[] | null = $state(null);

	onMount(async () => {
		const device = await getDevice(user, name);
		allowed_roles = device?.allowed_roles || [];
		ui_allowed_roles = device?.allowed_roles.map((role) => ({ value: role, label: role })) || [];
	});
</script>

<div>
	<div class="mb-4 text-3xl font-bold">
		{name}
	</div>
	{#if ui_allowed_roles === null}
		<div class="animated-pulse mt-4 h-10 w-full rounded bg-gray-100"></div>
	{:else}
		<form class="mt-4 flex flex-row items-center gap-4">
			<Select
				class="mt-4"
				items={Object.values(Role).map((role) => ({ value: role, label: role }))}
				bind:value={ui_allowed_roles}
				multiple
			/>
			<button
				type="button"
				class="rounded border px-4 py-2 hover:bg-gray-100 disabled:opacity-25"
				disabled={!ui_allowed_roles ||
					ui_allowed_roles.map((role) => role.value).toString() === allowed_roles.toString()}
				onclick={() => {
					if (!ui_allowed_roles) return;
					setDeviceRoles(
						user,
						name,
						ui_allowed_roles.map((role) => role.value)
					);
					allowed_roles = ui_allowed_roles.map((role) => role.value);
				}}
				aria-label="Spara"
			>
				Spara
			</button>
		</form>
	{/if}
</div>

<RecordingsGrid {user} device_name={name} />
