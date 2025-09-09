<script lang="ts">
	import Hls from 'hls.js';
	import type { HTMLVideoAttributes } from 'svelte/elements';

	const { id_token, src, ...rest }: { id_token?: string } & HTMLVideoAttributes = $props();

	let videoElement: HTMLVideoElement;
	let hls: Hls | null = null;

	const initialize = (): (() => void) | undefined => {
		if (!videoElement || !src) {
			return;
		}
		if (!src.endsWith('.m3u8')) {
			videoElement.src = src;
			return;
		}
		if (Hls.isSupported()) {
			const hls_config = id_token
				? {
						xhrSetup: (xhr: XMLHttpRequest) => {
							xhr.setRequestHeader('Authorization', `Bearer ${id_token}`);
						}
					}
				: undefined;
			hls = new Hls(hls_config);
			hls.loadSource(src);
			hls.attachMedia(videoElement);
			return () => {
				if (hls) {
					hls.destroy();
					hls = null;
				}
			};
		}
		throw new Error('Video not supported!');
	};

	$effect(() => {
		return initialize();
	});
</script>

<video bind:this={videoElement} {...rest}></video>
