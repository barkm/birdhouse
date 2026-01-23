<script lang="ts">
	import Users from '$lib/components/Users.svelte';
	import { user } from '$lib/firebase';
</script>

<Users user={$user!} />
