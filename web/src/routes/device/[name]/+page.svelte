<script lang="ts">
    import { page } from '$app/state';
	import Device from '$lib/components/Device.svelte';
	import { user } from '$lib/firebase';
</script>

<Device
    user={$user!}
    name={page.params.name!}
/>