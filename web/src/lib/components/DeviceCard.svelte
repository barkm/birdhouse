<script lang="ts">
	import { checkDeviceAvailability, getStatus, Role } from '$lib/recorder';
	import { setDeviceRoles } from '$lib/recorder';
	import type { User } from 'firebase/auth';
	import Select from 'svelte-select';

	interface Props {
		name: string;
		allowed_roles: Role[];
		active: boolean;
		user: User;
	}

	let { user, name, allowed_roles = $bindable(), active }: Props = $props();
	const status_promise = getStatus(user, name);
	const local_promise = checkDeviceAvailability(name);
	let ui_allowed_roles = $state(allowed_roles.map((role) => ({ value: role, label: role })));
</script>

<div class="rounded-lg border border-gray-300 p-4">
	<div class="flex items-center justify-between">
		<div class="text-xl font-semibold">{name}</div>
		{#await local_promise then local}
			{#if active}
				<div class="rounded bg-green-100 px-2 py-1 text-sm font-medium text-green-800">
					Aktiv {local ? '(Lokal)' : '(Fjärr)'}
				</div>
			{:else}
				<div class="rounded bg-gray-100 px-2 py-1 text-sm font-medium text-gray-800">
					Inaktiv {local ? '(Lokal)' : '(Fjärr)'}
				</div>
			{/if}
		{/await}
	</div>
	{#if active}
		{#await status_promise}
			<div class="rounded-log mt-3 mb-3 h-4 w-24 animate-pulse rounded bg-gray-300"></div>
		{:then status}
			<div class="mt-2 text-gray-600">Status: {status.status ?? 'Okänd'}</div>
		{/await}
	{/if}
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
</div>
