<script lang="ts">
	import { getUsers, Role, setUserRole } from '$lib/recorder';
    import type { User } from 'firebase/auth';
	import { onMount } from 'svelte';

    interface Props {
        user: User;
    }

    const { user }: Props = $props();

    let users: { uid: string; email: string; role: Role }[] | null = $state(null);

    const loadUsers = async () => {
        users = await getUsers(user);
    };

    onMount(loadUsers);

</script>

{#if users}
    <div class="flex flex-col gap-4">
        {#each users as u}
            <div class="p-4 border rounded-lg border-gray-300">
                <div class="font-semibold">{u.email}</div>
                <select bind:value={u.role} onchange={() => setUserRole(user, u.uid, u.role)} class="mt-2 p-2 border border-gray-300 rounded">
                    <option value="user">User</option>
                    <option value="admin">Admin</option>
                    <option value="none">None</option>
                </select>
            </div>
        {/each}
    </div>
{/if}