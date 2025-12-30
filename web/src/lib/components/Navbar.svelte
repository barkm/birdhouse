<script lang="ts">
    import { page } from '$app/state';
    let path = $derived(page.url.pathname);
</script>

{#snippet navLink(href, text)}
    <a 
        {href} 
        class="text-xl font-semibold px-4 py-2 border-b transition-colors -mb-px"
        class:border-black={path === href} 
        class:border-transparent={path !== href}
    >
        {text}
    </a>
{/snippet}

<div class="sticky top-0 z-50 bg-white border-b border-gray-300">
    <div class="flex gap-6 items-center justify-center">
        {@render navLink('/now', 'Now')}
        {@render navLink('/then', 'Then')}
    </div>
</div>