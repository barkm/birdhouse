<script lang="ts">
	import { page } from '$app/state';
	import { resolve } from '$app/paths';
	let path = $derived(page.url.pathname);

	interface Props {
		role: 'admin' | 'user' | null;
	}

	const { role }: Props = $props();
</script>

{#snippet navLink(href: '/now' | '/then' | '/devices' | '/users', text: string)}
	<a
		href={resolve(href)}
		class="-mb-px border-b px-4 py-2 text-xl font-semibold transition-colors"
		class:border-black={path === resolve(href)}
		class:border-transparent={path !== resolve(href)}
	>
		{text}
	</a>
{/snippet}

<div class="sticky top-0 z-50 bg-white">
	<div class="scrollbar-hide overflow-x-auto whitespace-nowrap">
		<div class="flex min-w-full w-max items-center gap-6 border-b border-gray-300 px-2 md:justify-center">
			{@render navLink('/now', 'Nu')}
			{@render navLink('/then', 'Då')}
			{#if role === 'admin'}
				{@render navLink('/devices', 'Enheter')}
				{@render navLink('/users', 'Användare')}
			{/if}
		</div>
	</div>
</div>


<style>
	.scrollbar-hide {
		-ms-overflow-style: none;
		scrollbar-width: none;
	}

	.scrollbar-hide::-webkit-scrollbar {
		display: none;
	}
</style>
