<script lang="ts">
	import './layout.css';
	import { loginWithGoogle, logout, user, isLoading } from '$lib/firebase';
	import { Role } from '$lib/recorder';
	import Navbar from '$lib/components/Navbar.svelte';
	import AnimatedKobbar from '$lib/components/loader/AnimatedKobbar.svelte';
	import { getRole } from '$lib/recorder';

	const { children } = $props();

	let role_promise = $derived($user ? getRole($user) : undefined);
</script>

{#if !$isLoading}
	{#if $user && role_promise !== undefined}
		{#await role_promise then role}
			{#if role}
				<div class="mx-auto max-w-4xl space-y-4 p-6">
					<Navbar {role} />
					{@render children()}
					<div class="grid place-items-center">
						<button class="rounded border border-black px-4 py-1 hover:bg-gray-100" onclick={logout}
							>Logga ut</button
						>
					</div>
				</div>
			{:else}
				<div class="flex h-screen flex-col items-center justify-center gap-10">
					<div class="w-3/4 max-w-sm">
						<AnimatedKobbar />
					</div>

					<p class="text-center text-lg">
						Din användare har ingen roll tilldelad. Vänligen kontakta en administratör för att få
						tillgång.
					</p>

					<button
						class="rounded border border-black px-4 py-1 transition hover:bg-gray-100"
						onclick={logout}
					>
						Logga ut
					</button>
				</div>
			{/if}
		{/await}
	{:else}
		<div class="flex h-screen flex-col items-center justify-center gap-10">
			<div class="w-3/4 max-w-sm">
				<AnimatedKobbar />
			</div>

			<button
				class="rounded border border-black px-4 py-1 transition hover:bg-gray-100"
				onclick={loginWithGoogle}
			>
				Logga in
			</button>
		</div>
	{/if}
{/if}
