<script lang="ts">
	import { getUsers, Role, setUserRole } from '$lib/recorder';
	import type { User } from 'firebase/auth';
	import { onMount } from 'svelte';
	import { asset } from '$app/paths';

	interface Props {
		user: User;
	}

	const { user }: Props = $props();

	let users: { id: string; email: string; role: Role | null, provider: string | null }[] | null = $state(null);

	const loadUsers = async () => {
		users = await getUsers(user);
	};

	onMount(loadUsers);
</script>

{#if users}
	<div class="flex flex-col gap-4">
		{#each users as u}
			<div class="rounded-lg border border-gray-300 p-4">
				<div class="flex items-center mb-2 gap-2">
				<img src={u.provider === 'google' ? asset('/google.svg') : asset('/firebase.svg')} alt="provider" class="inline-block w-5 h-5 ml-2 align-middle"/>
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
