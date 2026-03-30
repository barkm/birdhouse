<script lang="ts">
	import DateRangePicker from '$lib/components/DateRangePicker.svelte';
	import SensorCard from '$lib/components/SensorCard.svelte';
	import SensorLoader from '$lib/components/SensorLoader.svelte';
	import {
		getLocations,
		getSensorDataByLocation,
		type SensorData as OptionalSensorData
	} from '$lib/recorder';
	import { LineChart, Tooltip } from 'layerchart';
	import { format, PeriodType } from '@layerstack/utils';
	import { curveCatmullRom } from 'd3-shape';
	import Loader from '$lib/components/loader/Loader.svelte';
	import colors from 'tailwindcss/colors';
	import type { User } from 'firebase/auth';
	import RecordingsGrid from './RecordingsGrid.svelte';

	interface Props {
		user: User;
	}

	const { user }: Props = $props();

	const get_previous_day_from_midnight = () => {
		const date = new Date();
		date.setDate(date.getDate() - 2);
		return date;
	};

	let start_date = $state(get_previous_day_from_midnight());
	let end_date = $state(new Date());

	const CHART_COLORS = [colors.blue[400], colors.amber[400], colors.green[400], colors.rose[400]];

	const average = (arr: number[]) => {
		if (arr.length === 0) return 0;
		const sum = arr.reduce((a, b) => a + b, 0);
		return sum / arr.length;
	};

	interface SensorData {
		created_at: Date;
		temperature: number;
		humidity: number;
	}

	const filter_sensor_data = (data: OptionalSensorData[]): SensorData[] => {
		return data.filter(
			(d) => d.temperature !== undefined && d.humidity !== undefined
		) as SensorData[];
	};

	const average_sensor_data = (data: SensorData[]) => {
		const temperatures = data.map((d) => d.temperature);
		const humidities = data.map((d) => d.humidity);
		return {
			temperature: average(temperatures),
			humidity: average(humidities)
		};
	};

	const get_temperature_limits = (data: SensorData[]) => {
		if (data.length === 0) return null;
		const temperatures = data.map((d) => d.temperature);
		return {
			max: temperatures.reduce((a, b) => Math.max(a, b), -Infinity),
			min: temperatures.reduce((a, b) => Math.min(a, b), Infinity)
		};
	};

	const capitalize = (s: string) => s.charAt(0).toUpperCase() + s.slice(1);

	const location_data_promise = $derived(
		(() => {
			const start = start_date;
			const end = end_date;
			return getLocations(user).then((locs) =>
				Promise.all(
					locs.map(async (loc, i) => {
						const raw = await getSensorDataByLocation(user, loc.name, start, end);
						const filtered = filter_sensor_data(raw);
						return {
							name: loc.name,
							color: CHART_COLORS[i % CHART_COLORS.length],
							data: filtered,
							average: average_sensor_data(filtered),
							limits: get_temperature_limits(filtered)
						};
					})
				)
			);
		})()
	);
</script>

<DateRangePicker bind:start_date bind:end_date />
<div class="grid grid-cols-2 gap-4">
	{#await location_data_promise}
		<SensorLoader limits />
		<SensorLoader limits />
	{:then location_data}
		{#each location_data as loc}
			<SensorCard
				title={capitalize(loc.name)}
				temperature={loc.average.temperature}
				temperature_limits={loc.limits ?? undefined}
				humidity={loc.average.humidity}
			/>
		{/each}
	{/await}
</div>
{#await location_data_promise}
	<div class="h-[300px]">
		<Loader />
	</div>
{:then location_data}
	{@const valid_limits = location_data.map((l) => l.limits).filter((l) => l !== null)}
	{@const y_domain =
		valid_limits.length > 0
			? [
					Math.min(...valid_limits.map((l) => l.min)) - 5,
					Math.max(...valid_limits.map((l) => l.max)) + 5
				]
			: [-10, 30]}
	<div class="h-[300px] rounded-lg border border-gray-300 p-4">
		<LineChart
			x="created_at"
			y="temperature"
			series={location_data.map((loc) => ({
				key: capitalize(loc.name),
				data: loc.data.map((d) => ({ ...d, sensor: capitalize(loc.name) })),
				color: loc.color,
				props: { strokeWidth: 2 }
			}))}
			renderContext="svg"
			yDomain={y_domain}
			legend
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
			{#snippet tooltip({ context, series })}
				{@const activeSeriesColor = series.find(
					(s) => s.key === context.tooltip.data?.sensor
				)?.color}
				<Tooltip.Root>
					{#snippet children({ data })}
						<Tooltip.Header
							>{format(context.x(data), {
								type: PeriodType.DayTime,
								locale: 'sv-SE'
							})}</Tooltip.Header
						>
						<Tooltip.List>
							<Tooltip.Item
								label={data.sensor}
								value={data.temperature.toFixed(1) + ' °C'}
								color={activeSeriesColor}
							/>
						</Tooltip.List>
					{/snippet}
				</Tooltip.Root>
			{/snippet}
		</LineChart>
	</div>
	{#each location_data as loc}
		<RecordingsGrid {user} location_name={loc.name} from={start_date} to={end_date} />
	{/each}
{/await}
