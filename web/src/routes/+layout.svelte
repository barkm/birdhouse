<script lang="ts">
	import './layout.css';
	import { loginWithGoogle, logout, user, isLoading } from "$lib/firebase";
	import Loader from '$lib/components/loader/Loader.svelte';

	const { children } = $props();
</script>

{#if !$isLoading}
    {#if $user}
        {@render children()}
        <div class="grid place-items-center">
            <button class="border border-black rounded px-4 py-1 hover:bg-gray-100" onclick={logout}>Logga ut</button>
        </div>
    {:else}
    <div class="h-screen flex flex-col justify-center items-center gap-4">
        
        <div class="w-3/4 max-w-sm">
            <Loader />
        </div>

        <button 
            class="border border-black rounded px-4 py-1 hover:bg-gray-100 transition" 
            onclick={loginWithGoogle}
        >
            Logga in
        </button>
    </div>
    {/if}
{/if}