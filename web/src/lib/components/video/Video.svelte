<script lang="ts">
	import Hls from 'hls.js';
	import type { HTMLVideoAttributes } from 'svelte/elements';

	const { id_token, src, ...rest }: { id_token?: string } & HTMLVideoAttributes = $props();

	let videoElement: HTMLVideoElement;
	let hls: Hls | null = null;

	const get_hls_config = () => {
		return id_token
			? {
					xhrSetup: (xhr: XMLHttpRequest) => {
						xhr.setRequestHeader('Authorization', `Bearer ${id_token}`);
					}
				}
			: undefined;
	};

	const initialize = (): (() => void) | undefined => {
		if (!videoElement || !src) {
			return;
		}
		if (!src.endsWith('.m3u8')) {
			videoElement.src = src;
			return;
		}
		if (!Hls.isSupported()) {
			throw new Error('HLS not supported!');
		}
		hls = new Hls(get_hls_config());
		hls.loadSource(src);
		hls.attachMedia(videoElement);
		// The playlist 404s until the camera has produced its first segment,
		// so keep retrying network errors while the stream warms up.
		let retries = 0;
		hls.on(Hls.Events.ERROR, (_, data) => {
			if (!hls || !data.fatal) {
				return;
			}
			if (data.type === Hls.ErrorTypes.NETWORK_ERROR && retries < 30) {
				retries += 1;
				setTimeout(() => hls?.startLoad(), 1000);
			} else if (data.type === Hls.ErrorTypes.MEDIA_ERROR) {
				hls.recoverMediaError();
			} else {
				hls.destroy();
				hls = null;
			}
		});
		return () => {
			if (hls) {
				hls.destroy();
				hls = null;
			}
		};
	};

	$effect(() => {
		return initialize();
	});
</script>

<video bind:this={videoElement} {...rest}></video>
