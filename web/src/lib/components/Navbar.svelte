<script lang="ts">
	import { page } from '$app/state';
	import { resolve } from '$app/paths';
	import { role } from '$lib/firebase';
	let path = $derived(page.url.pathname);
</script>

{#snippet navLink(href: '/now' | '/then' | '/devices', text: string)}
	<a
		href={resolve(href)}
		class="-mb-px border-b px-4 py-2 text-xl font-semibold transition-colors"
		class:border-black={path === resolve(href)}
		class:border-transparent={path !== resolve(href)}
	>
		{text}
	</a>
{/snippet}

<div class="sticky top-0 z-50 border-b border-gray-300 bg-white">
	<div class="flex items-center justify-center gap-6">
		{@render navLink('/now', 'Nu')}
		{@render navLink('/then', 'Då')}
		{#if $role === 'admin'}
			{@render navLink('/devices', 'Enheter')}
		{/if}
	</div>
</div>
