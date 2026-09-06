<script lang="ts">
	import type { User } from 'firebase/auth';
	import { getSensorData } from '$lib/recorder';
	import Loader from '$lib/components/loader/Loader.svelte';
	import { LineChart, Tooltip } from 'layerchart';
	import { format, PeriodType } from '@layerstack/utils';
	import { curveCatmullRom } from 'd3-shape';
	import colors from 'tailwindcss/colors';

	interface Props {
		user: User;
		device_name: string;
		start_date: Date;
		end_date: Date;
	}

	const { user, device_name, start_date, end_date }: Props = $props();

	type Aspect = 'temperature' | 'humidity' | 'cpu_temperature';

	let aspect = $state<Aspect>('temperature');

	const unit = $derived(aspect === 'humidity' ? '%' : '°C');

	const sensor_data_promise = $derived(getSensorData(user, device_name, start_date, end_date));

	// A failed reading comes back without a value, and is kept rather than filtered
	// out: the chart breaks its line wherever a point has no value, so the missing
	// period shows up as a gap instead of a straight line drawn across it.
	const chart_data_promise = $derived.by(() => {
		const currentAspect = aspect;
		return sensor_data_promise.then((data) =>
			data
				.map((d) => ({ created_at: d.created_at, value: d[currentAspect] }))
				.sort((a, b) => a.created_at.getTime() - b.created_at.getTime())
		);
	});

	const y_domain_promise = $derived(
		chart_data_promise.then((data) => {
			const values = data.map((d) => d.value).filter((v) => v !== undefined);
			if (values.length === 0) return [0, 1];
			const min = values.reduce((a, b) => Math.min(a, b), Infinity);
			const max = values.reduce((a, b) => Math.max(a, b), -Infinity);
			return [min - 5, max + 5];
		})
	);
</script>

<div class="flex flex-wrap items-center gap-2">
	<select
		bind:value={aspect}
		class="rounded-md border border-gray-300 bg-white p-2 text-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
	>
		<option value="temperature">Temperatur</option>
		<option value="humidity">Luftfuktighet</option>
		<option value="cpu_temperature">CPU-temperatur</option>
	</select>
</div>

{#await Promise.all([chart_data_promise, y_domain_promise])}
	<div class="h-[300px]">
		<Loader />
	</div>
{:then [data, y_domain]}
	{#if data.every((d) => d.value === undefined)}
		<div
			class="flex h-[300px] items-center justify-center rounded-lg border border-gray-300 text-gray-400"
		>
			Inga data för denna period
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
									value={d.value !== undefined ? d.value.toFixed(1) + ' ' + unit : 'Inga data'}
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
