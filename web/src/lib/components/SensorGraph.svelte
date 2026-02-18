<script lang="ts">
	import type { User } from 'firebase/auth';
	import { getSensorData } from '$lib/recorder';
	import DateRangePicker from '$lib/components/DateRangePicker.svelte';
	import Loader from '$lib/components/loader/Loader.svelte';
	import { LineChart, Tooltip } from 'layerchart';
	import { format, PeriodType } from '@layerstack/utils';
	import { curveCatmullRom } from 'd3-shape';
	import colors from 'tailwindcss/colors';

	interface Props {
		user: User;
		device_name: string;
	}

	const { user, device_name }: Props = $props();

	type Aspect = 'temperature' | 'humidity';

	const get_previous_days = () => {
		const date = new Date();
		date.setDate(date.getDate() - 6);
		return date;
	};

	let start_date = $state(get_previous_days());
	let end_date = $state(new Date());
	let aspect = $state<Aspect>('temperature');

	const unit = $derived(aspect === 'temperature' ? '°C' : '%');

	const sensor_data_promise = $derived(getSensorData(user, device_name, start_date, end_date));

	const filtered_data_promise = $derived.by(() => {
		const currentAspect = aspect;
		return sensor_data_promise.then((data) =>
			data
				.filter((d) => d[currentAspect] !== undefined)
				.map((d) => ({ ...d, value: d[currentAspect] as number }))
		);
	});

	const y_domain_promise = $derived(
		filtered_data_promise.then((data) => {
			if (data.length === 0) return [0, 1];
			const values = data.map((d) => d.value);
			const min = values.reduce((a, b) => Math.min(a, b), Infinity);
			const max = values.reduce((a, b) => Math.max(a, b), -Infinity);
			return [min - 5, max + 5];
		})
	);
</script>

<div class="flex flex-wrap items-center gap-2">
	<DateRangePicker bind:start_date bind:end_date />
	<select
		bind:value={aspect}
		class="rounded-md border border-gray-300 bg-white p-2 text-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
	>
		<option value="temperature">Temperature</option>
		<option value="humidity">Humidity</option>
	</select>
</div>

{#await Promise.all([filtered_data_promise, y_domain_promise])}
	<div class="h-[300px]">
		<Loader />
	</div>
{:then [data, y_domain]}
	{#if data.length === 0}
		<div class="flex h-[300px] items-center justify-center rounded-lg border border-gray-300 text-gray-400">
			No data for this period
		</div>
	{:else}
		<div class="h-[300px] rounded-lg border border-gray-300 p-4">
			<LineChart
				x="created_at"
				y="value"
				series={[
					{
						key: device_name,
						data,
						color: colors.blue[400],
						props: { strokeWidth: 2 }
					}
				]}
				renderContext="svg"
				yDomain={y_domain}
				props={{
					spline: { curve: curveCatmullRom },
					xAxis: {
						format: (value) =>
							format(value, (d) =>
								Intl.DateTimeFormat('sv-SE', {
									hour: '2-digit',
									minute: '2-digit',
									day: '2-digit',
									month: '2-digit'
								}).format(d)
							)
					}
				}}
			>
				{#snippet tooltip({ context })}
					<Tooltip.Root>
						{#snippet children({ data: d })}
							<Tooltip.Header>
								{format(context.x(d), { type: PeriodType.DayTime, locale: 'sv-SE' })}
							</Tooltip.Header>
							<Tooltip.List>
								<Tooltip.Item
									label={aspect}
									value={d.value.toFixed(1) + ' ' + unit}
									color={colors.blue[400]}
								/>
							</Tooltip.List>
						{/snippet}
					</Tooltip.Root>
				{/snippet}
			</LineChart>
		</div>
	{/if}
{/await}