<script lang="ts">
	import type { User } from 'firebase/auth';
	import RecordingsGrid from './RecordingsGrid.svelte';
	import SensorGraph from './SensorGraph.svelte';
	import { getDevice, Role, setDeviceRoles, startAndGetStreamUrl } from '$lib/recorder';
	import { onMount } from 'svelte';
	import Select from 'svelte-select';
	import VideoWithLoader from './video/VideoWithLoader.svelte';

	interface Props {
		user: User;
		name: string;
	}

	const { user, name }: Props = $props();

	let allowed_roles: string[] = $state([]);
	let ui_allowed_roles: { value: Role; label: string }[] | null = $state(null);

	type StreamState = 'loading' | 'unavailable' | { url: string; token: string };
	let stream: StreamState = $state('loading');

	const get_previous_days = () => {
		const date = new Date();
		date.setDate(date.getDate() - 6);
		return date;
	};

	const from = get_previous_days();
	const to = new Date();

	onMount(async () => {
		const device = await getDevice(user, name);
		allowed_roles = device?.allowed_roles || [];
		ui_allowed_roles =
			device?.allowed_roles
				.filter((role) => role !== Role.ADMIN)
				.map((role) => ({ value: role, label: role })) || [];

		const [url, token] = await Promise.all([startAndGetStreamUrl(user, name), user.getIdToken()]);
		stream = url ? { url, token } : 'unavailable';
	});
</script>

<div>
	<div class="mb-4 text-3xl font-bold">
		{name}
	</div>
	{#if ui_allowed_roles === null}
		<div class="animated-pulse mt-4 h-10 w-full rounded bg-gray-100"></div>
	{:else}
		<form class="mt-4 flex flex-row items-center gap-4">
			<Select
				class="mt-4"
				items={Object.values(Role)
					.filter((role) => role !== Role.ADMIN)
					.map((role) => ({ value: role, label: role }))}
				bind:value={ui_allowed_roles}
				multiple
			/>
			<button
				type="button"
				class="rounded border px-4 py-2 hover:bg-gray-100 disabled:opacity-25"
				disabled={!ui_allowed_roles ||
					ui_allowed_roles.map((role) => role.value).toString() ===
						allowed_roles.filter((r) => r !== Role.ADMIN).toString()}
				onclick={() => {
					if (!ui_allowed_roles) return;
					const roles = [Role.ADMIN, ...ui_allowed_roles.map((role) => role.value)];
					setDeviceRoles(user, name, roles);
					allowed_roles = roles;
				}}
				aria-label="Spara"
			>
				Spara
			</button>
		</form>
	{/if}
</div>

{#if stream === 'unavailable'}
	<div class="flex w-full items-center justify-center rounded-lg bg-gray-100 text-gray-400" style="aspect-ratio: 16/9">
		No stream available
	</div>
{:else}
	<VideoWithLoader
		id_token={typeof stream === 'object' ? stream.token : undefined}
		src={typeof stream === 'object' ? stream.url : undefined}
		autoplay
		muted
		playsinline
		controls
	/>
{/if}

<SensorGraph {user} device_name={name} />

<RecordingsGrid {user} device_name={name} {from} {to} />
