<script lang="ts">
	import { getUsers } from '$lib/recorder';
    import type { User } from 'firebase/auth';

    interface Props {
        user: User;
    }

    const { user }: Props = $props();

    const users_promise = $derived(getUsers(user));

</script>

{#await users_promise then users}
    <div class="flex flex-col gap-4">
        {#each users as u}
            <div class="p-4 border rounded-lg border-gray-300">
                <div class="font-semibold">{u.email}</div>
                <div class="text-sm text-gray-600">Roll: {u.role}</div>
            </div>
        {/each}
    </div>
{/await}