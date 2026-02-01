<script lang="ts">
	import { getRecordings, type Recording } from '$lib/recorder';
	import type { User } from 'firebase/auth';
	import Loader from './loader/Loader.svelte';
	import VideoWithLoader from './video/VideoWithLoader.svelte';

	interface Props {
		user: User;
		device_name: string;
		from?: Date;
		to?: Date;
	}

	const { user, device_name, from, to }: Props = $props();
	const compare_recordings = (a: Recording, b: Recording) => {
		return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
	};

	const recordings_promise = getRecordings(user, device_name, from, to).then((recordings) =>
		recordings.sort(compare_recordings)
	);
</script>

<div class="grid grid-cols-1 gap-4 md:grid-cols-2">
	{#await recordings_promise}
		{#each Array(4) as _}
			<div class="flex aspect-video flex-col items-center justify-center">
				<div class="mb-3 h-4 w-30 rounded bg-gray-100"></div>
				<Loader />
			</div>
		{/each}
	{:then recordings}
		{#each recordings as recording}
			<div>
				<span class="mb-2 block text-center text-sm text-gray-600">
					{new Date(recording.created_at).toLocaleString()}
				</span>
				<VideoWithLoader
					class="w-full rounded-sm"
					src={recording.url}
					controls
					autoplay
					playsinline
					muted
					loop
				/>
			</div>
		{/each}
	{/await}
</div>
