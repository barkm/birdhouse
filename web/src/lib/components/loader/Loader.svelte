<script lang="ts">
	import Kobbar from './kobbar.svelte';
</script>

<div class="h-full w-full bg-gray-100 rounded-lg">
	<div class="w-1/3 relative top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2">
		<Kobbar />
	</div>
</div>

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
		animation: jitter 3s infinite linear;
	}
	:global(.bird:nth-of-type(1)) {
		animation-delay: -0.25s;
	}
	:global(.bird:nth-of-type(2)) {
		animation-delay: -0.5s;
	}
	:global(.bird:nth-of-type(3)) {
		animation-delay: -0.75s;
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
		animation: wave 3s infinite ease;
	}
	:global(.reflection:nth-of-type(1)) {
		animation-delay: 0.5s;
	}
	:global(.reflection:nth-of-type(2)) {
		animation-delay: 1s;
	}
</style>
