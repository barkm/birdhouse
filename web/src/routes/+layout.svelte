<script lang="ts">
	import './layout.css';
	import { loginWithGoogle, logout, user, isLoading } from '$lib/firebase';
	import Loader from '$lib/components/loader/Loader.svelte';
	import Navbar from '$lib/components/Navbar.svelte';

	const { children } = $props();
</script>

{#if !$isLoading}
	{#if $user}
		<div class="mx-auto max-w-4xl p-6 space-y-4">
		<Navbar />
		{@render children()}
		<div class="grid place-items-center">
			<button class="rounded border border-black px-4 py-1 hover:bg-gray-100" onclick={logout}
				>Logga ut</button
			>
		</div>
		</div>
	{:else}
		<div class="flex h-screen flex-col items-center justify-center gap-4">
			<div class="w-3/4 max-w-sm">
				<Loader />
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
