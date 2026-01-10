<script lang="ts">
	import DateRangePicker from '$lib/components/DateRangePicker.svelte';
	import SensorCard from '$lib/components/SensorCard.svelte';
	import SensorLoader from '$lib/components/SensorLoader.svelte';
	import { user } from '$lib/firebase';
	import {
		getRecordings,
		getSensorData,
		type Recording,
		type SensorData as OptionalSensorData
	} from '$lib/recorder';
	import { LineChart, Tooltip } from 'layerchart';
	import { format, PeriodType } from '@layerstack/utils';
	import { curveCatmullRom } from 'd3-shape';
	import VideoWithLoader from '$lib/components/video/VideoWithLoader.svelte';
	import Loader from '$lib/components/loader/Loader.svelte';
	import colors from 'tailwindcss/colors';

	const get_previous_day_from_midnight = () => {
		const date = new Date();
		date.setDate(date.getDate() - 2);
		return date;
	};

	let start_date = $state(get_previous_day_from_midnight());
	let end_date = $state(new Date());

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
		const temperatures = data.map((d) => d.temperature);
		return {
			max: Math.max(...temperatures),
			min: Math.min(...temperatures)
		};
	};

	const compare_recordings = (a: Recording, b: Recording) => {
		return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
	};

	const outside_sensor_data_promise = $derived(
		getSensorData($user!, 'birdhouse', start_date, end_date)
	);
	const inside_sensor_data_promise = $derived(getSensorData($user!, 'house', start_date, end_date));

	const filtered_outside_sensor_data_promise = $derived(
		outside_sensor_data_promise.then(filter_sensor_data)
	);
	const filtered_inside_sensor_data_promise = $derived(
		inside_sensor_data_promise.then(filter_sensor_data)
	);

	const outside_temperature_limits_promise = $derived(
		filtered_outside_sensor_data_promise.then(get_temperature_limits)
	);
	const inside_temperature_limits_promise = $derived(
		filtered_inside_sensor_data_promise.then(get_temperature_limits)
	);
	const average_outside_sensor_promise = $derived(
		filtered_outside_sensor_data_promise.then(average_sensor_data)
	);
	const average_inside_sensor_promise = $derived(
		filtered_inside_sensor_data_promise.then(average_sensor_data)
	);

	const recordings_promise = $derived(
		getRecordings($user!, 'birdhouse', start_date, end_date).then((recordings) =>
			recordings.sort(compare_recordings)
		)
	);
</script>

<DateRangePicker bind:start_date bind:end_date />
<div class="grid grid-cols-2 gap-4">
	{#await Promise.all([average_outside_sensor_promise, outside_temperature_limits_promise])}
		<SensorLoader limits />
	{:then [average_outside_sensor, outside_temperature_limits]}
		<SensorCard
			title={'Utomhus'}
			temperature={average_outside_sensor.temperature}
			temperature_limits={outside_temperature_limits}
			humidity={average_outside_sensor.humidity}
		/>
	{/await}
	{#await Promise.all([average_inside_sensor_promise, inside_temperature_limits_promise])}
		<SensorLoader limits />
	{:then [average_inside_sensor, inside_temperature_limits]}
		<SensorCard
			title={'Inomhus'}
			temperature={average_inside_sensor.temperature}
			temperature_limits={inside_temperature_limits}
			humidity={average_inside_sensor.humidity}
		/>
	{/await}
</div>
{#await Promise.all( [filtered_outside_sensor_data_promise, filtered_inside_sensor_data_promise, outside_temperature_limits_promise, inside_temperature_limits_promise] )}
	<div class="h-[300px]">
		<Loader />
	</div>
{:then [outside_data, inside_data, outside_limits, inside_limits]}
	<div class="h-[300px] rounded-lg border border-gray-300 p-4">
		<LineChart
			x="created_at"
			y="temperature"
			series={[
				{
					key: 'Utomhus',
					data: outside_data.map((d) => ({ ...d, sensor: 'Utomhus' })),
					color: colors.blue[400],
					props: {
						strokeWidth: 2
					}
				},
				{
					key: 'Inomhus',
					data: inside_data.map((d) => ({ ...d, sensor: 'Inomhus' })),
					color: colors.amber[400],
					props: {
						strokeWidth: 2
					}
				}
			]}
			renderContext="svg"
			yDomain={[
				Math.min(outside_limits.min, inside_limits.min) - 5,
				Math.max(outside_limits.max, inside_limits.max) + 5
			]}
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
{/await}
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
