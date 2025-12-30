<script lang="ts">
	import Device from '$lib/components/Device.svelte';
	import { loginWithGoogle, logout, user } from '$lib/firebase';
	import Loader from '$lib/components/loader/Loader.svelte';
</script>

{#if $user}
	<column style="width: 100%">
		<Device device={{ name: 'zero' }} />
		<button onclick={logout}>Logga ut</button>
	</column>
{:else}
	<row>
		<column style="width: 25%">
			<Loader />
			<button onclick={loginWithGoogle}>Logga in</button>
		</column>
	</row>
{/if}

<style>
	row {
		width: 100%;
		height: 100vh;
		display: flex;
		justify-content: center;
		align-items: center;
	}

	column {
		min-width: 300px;
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 5rem;
	}

	button {
		padding: 0.5rem 1rem;
		font-size: 1.2rem;
		background-color: white;
		color: black;
		border: 1px solid black;
		border-radius: none;
		cursor: pointer;
	}

	button:hover {
		background-color: black;
		color: white;
	}
</style>
