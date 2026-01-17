<script lang="ts">
	import Then from '$lib/components/Then.svelte';
	import { user } from '$lib/firebase';
</script>

<Then user={$user!} />
