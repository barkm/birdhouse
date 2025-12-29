<script lang="ts">
	import Now from "$lib/components/Now.svelte";
    import { user } from "$lib/firebase";

</script>

<Now user={$user!} />