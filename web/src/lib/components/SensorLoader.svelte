<script lang="ts">
	interface Props {
		limits: boolean;
	}

	const { limits }: Props = $props();
</script>

<div class="animate-pulse rounded-lg bg-gray-100 p-4">
	<div class="mb-3 h-4 w-24 rounded bg-gray-300"></div>
	<br />
	<div class="mb-2 h-8 w-32 rounded bg-gray-300"></div>
	{#if limits}
		<div class="mb-2 h-2 w-32 rounded bg-gray-300"></div>
	{/if}
	<div class="h-3 w-16 rounded bg-gray-300"></div>
</div>
