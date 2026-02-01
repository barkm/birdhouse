<script lang="ts">
	import { resolve } from '$app/paths';
	import { checkDeviceAvailability, getStatus, Role } from '$lib/recorder';
	import type { User } from 'firebase/auth';

	interface Props {
		name: string;
		allowed_roles: Role[];
		active: boolean;
		user: User;
	}

	let { user, name, allowed_roles = $bindable(), active }: Props = $props();
	const status_promise = getStatus(user, name);
	const local_promise = checkDeviceAvailability(name);
</script>

<a class="rounded-lg border border-gray-300 p-4 text-left" href={resolve(`/device/${name}`)}>
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
</a>
