<script lang="ts">
	import { page } from '$app/state';
	let path = $derived(page.url.pathname);
</script>

{#snippet navLink(href, text)}
	<a
		{href}
		class="-mb-px border-b px-4 py-2 text-xl font-semibold transition-colors"
		class:border-black={path === href}
		class:border-transparent={path !== href}
	>
		{text}
	</a>
{/snippet}

<div class="sticky top-0 z-50 border-b border-gray-300 bg-white">
	<div class="flex items-center justify-center gap-6">
		{@render navLink('/now', 'Now')}
		{@render navLink('/then', 'Then')}
	</div>
</div>
