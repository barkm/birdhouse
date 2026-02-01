<script lang="ts">
	import { page } from '$app/state';
	import Device from '$lib/components/Device.svelte';
	import { user } from '$lib/firebase';

	const name = $derived(page.url.searchParams.get('name'));
</script>

{#if name !== null}
	<Device user={$user!} {name} />
{/if}
