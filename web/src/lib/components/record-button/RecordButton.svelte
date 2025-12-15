<script lang="ts">
	import { fade } from 'svelte/transition';
	import { Recorder } from './recorder';
	import recordingSvg from './recording.svg';
	import recordSvg from './record.svg';

	interface Props {
		video: HTMLVideoElement | null;
	}

	let { video }: Props = $props();
	const can_capture_video = (): boolean => {
		return typeof (HTMLVideoElement.prototype as any).captureStream === 'function';
	};

	let recorder: Recorder | null = $derived.by(() => {
		if (!video || !can_capture_video()) {
			return null;
		}
		const stream = (
			video as HTMLVideoElement & { captureStream: () => MediaStream }
		).captureStream();
		return new Recorder(stream);
	});

	let recording = $state(false);
</script>

{#if recorder}
	<recording-button>
		<button
			onclick={async () => {
				recording = !recording;
				if (!recorder) {
					return;
				}
				if (recording) {
					recorder.start();
				} else {
					const blob = await recorder.stop();
					const link = document.createElement('a');
					link.href = URL.createObjectURL(blob);
					link.download = 'recording.webm';
					link.click();
				}
			}}
			aria-pressed={recording}
			>
			{#if recording}
				<img in:fade src={recordingSvg} alt="Stop Recording" />
			{:else}
				<img in:fade src={recordSvg} alt="Record" />
			{/if}
		</button>
	</recording-button>
{/if}

<style>
	recording-button button {
		background: none;
		border: none;
		cursor: pointer;
		border-radius: 100%;
	}

	@keyframes spin {
		from {
			transform: rotate(0deg);
		}
		to {
			transform: rotate(360deg);
		}
	}

	recording-button button img {
		animation: spin 2s linear infinite; /* rotates once every 2s */
		width: 40px;
	}
</style>
