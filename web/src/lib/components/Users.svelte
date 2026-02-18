<script lang="ts">
	import { getUsers, Role, setUserRole } from '$lib/recorder';
	import type { User } from 'firebase/auth';
	import { onMount } from 'svelte';
	import { asset } from '$app/paths';

	interface Props {
		user: User;
	}

	const { user }: Props = $props();

	let users: { id: string; email: string; role: Role | null; provider: string | null }[] | null =
		$state(null);

	const loadUsers = async () => {
		users = await getUsers(user);
	};

	onMount(loadUsers);
</script>

{#if users}
	<div class="flex flex-col gap-4">
		{#each users as u}
			<div class="rounded-lg border border-gray-300 p-4">
				<div class="mb-2 flex items-center gap-2 overflow-x-auto">
				{#if u.provider === 'google'}
					<img src={asset('/google.svg')} alt="google" class="ml-2 inline-block h-5 w-5 align-middle" />
				{:else if u.provider === 'firebase'}
					<img src={asset('/firebase.svg')} alt="firebase" class="ml-2 inline-block h-5 w-5 align-middle" />
				{:else}
					<span class="ml-2 inline-flex h-5 w-5 items-center justify-center rounded-full bg-gray-200 text-xs text-gray-500 align-middle">?</span>
				{/if}
					<span class="font-semibold">{u.email}</span>
				</div>
				<select
					bind:value={u.role}
					onchange={() => setUserRole(user, u.id, u.role)}
					class="mt-2 rounded border border-gray-300 p-2"
				>
					<option value="user">User</option>
					<option value="admin">Admin</option>
					<option value={null}>None</option>
				</select>
			</div>
		{/each}
	</div>
{/if}
