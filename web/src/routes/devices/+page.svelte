<script lang="ts">
	import Devices from "$lib/components/Devices.svelte";
	import { user } from "$lib/firebase";
</script>

<Devices user={$user!} />