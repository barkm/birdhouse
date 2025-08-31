<script lang="ts">
	import Kobbar from '$lib/kobbar.svelte';
</script>

<Kobbar />

<style>
	@keyframes jitter {
		0% {
			transform: translate(0, 0);
		}
		25% {
			transform: translate(2px, 2px);
		}
		50% {
			transform: translate(-3px, 1px);
		}
		75% {
			transform: translate(1px, -2px);
		}
		100% {
			transform: translate(0, 0);
		}
	}

	:global(.bird) {
		animation: jitter 1s infinite steps(1, end);
	}
	:global(.bird:nth-of-type(1)) {
		animation-delay: -0.1s;
	}
	:global(.bird:nth-of-type(2)) {
		animation-delay: -0.2s;
	}
	:global(.bird:nth-of-type(3)) {
		animation-delay: -0.3s;
	}

	@keyframes wave {
		0% {
			transform: translate(0, 0);
		}
		50% {
			transform: translate(0px, 1.5px);
		}
		100% {
			transform: translate(0, 0);
		}
	}

	:global(.reflection) {
		animation: wave 1.5s infinite steps(1, end);
	}
    :global(.reflection:nth-of-type(1)) {
        animation-delay: 0.25s;
    }
    :global(.reflection:nth-of-type(2)) {
        animation-delay: 0.5s;
    }
</style>
