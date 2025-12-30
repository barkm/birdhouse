<script lang="ts">
	import DateRangePicker from '$lib/components/DateRangePicker.svelte';
	import SensorCard from '$lib/components/SensorCard.svelte';
	import SensorLoader from '$lib/components/SensorLoader.svelte';
	import { user } from '$lib/firebase';
	import { getRecordings, getSensorData, type SensorData } from '$lib/recorder';
	import { LineChart, Tooltip } from 'layerchart';
	import { format, PeriodType } from '@layerstack/utils';
	import { curveCatmullRom } from 'd3-shape';
	import VideoWithLoader from '$lib/components/video/VideoWithLoader.svelte';

	let start_date = $state(new Date(new Date().setDate(new Date().getDate() - 7)));
	let end_date = $state(new Date());

	const average = (arr: number[]) => {
		if (arr.length === 0) return 0;
		const sum = arr.reduce((a, b) => a + b, 0);
		return sum / arr.length;
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

	const outside_sensor_data_promise = $derived(
		getSensorData($user!, 'birdhouse', start_date, end_date)
	);
	const inside_sensor_data_promise = $derived(getSensorData($user!, 'house', start_date, end_date));
	const outside_temperature_limits_promise = $derived(
		outside_sensor_data_promise.then(get_temperature_limits)
	);
	const inside_temperature_limits_promise = $derived(
		inside_sensor_data_promise.then(get_temperature_limits)
	);
	const average_outside_sensor_promise = $derived(
		outside_sensor_data_promise.then(average_sensor_data)
	);
	const average_inside_sensor_promise = $derived(
		inside_sensor_data_promise.then(average_sensor_data)
	);

	const recordings_promise = $derived(getRecordings($user!, 'birdhouse', start_date, end_date));
</script>

<div class="mx-auto max-w-4xl space-y-4 p-6">
	<DateRangePicker bind:start_date bind:end_date />
	<div class="grid grid-cols-2 gap-4">
		{#await Promise.all([average_outside_sensor_promise, outside_temperature_limits_promise])}
			<SensorLoader />
		{:then [average_outside_sensor, outside_temperature_limits]}
			<SensorCard
				title={'Utomhus'}
				temperature={average_outside_sensor.temperature}
				temperature_limits={outside_temperature_limits}
				humidity={average_outside_sensor.humidity}
			/>
		{/await}
		{#await Promise.all([average_inside_sensor_promise, inside_temperature_limits_promise])}
			<SensorLoader />
		{:then [average_inside_sensor, inside_temperature_limits]}
			<SensorCard
				title={'Inomhus'}
				temperature={average_inside_sensor.temperature}
				temperature_limits={inside_temperature_limits}
				humidity={average_inside_sensor.humidity}
			/>
		{/await}
	</div>
	{#await Promise.all([outside_sensor_data_promise, inside_sensor_data_promise])}
		<div class="h-[300px] animate-pulse rounded-sm border border-gray-300 p-4">
			<div class="mb-3 h-4 w-24 rounded bg-gray-300"></div>
			<div class="mb-2 h-8 w-full rounded bg-gray-300"></div>
			<div class="h-3 w-16 rounded bg-gray-300"></div>
			<div class="mt-2 h-20 w-full rounded bg-gray-300"></div>
			<div class="mt-2 h-3 w-3/4 rounded bg-gray-300"></div>
			<div class="mt-2 h-10 w-full rounded bg-gray-300"></div>
			<div class="mt-2 h-3 w-3/4 rounded bg-gray-300"></div>
		</div>
	{:then [outside_data, inside_data]}
		<div class="h-[300px] rounded-sm border border-gray-300 p-4">
			<LineChart
				x="created_at"
				y="temperature"
				series={[
					{
						key: 'Utomhus',
						data: outside_data.map((d) => ({ ...d, sensor: 'Utomhus' })), // Calibration offset
						color: '#1f77b4'
					},
					{
						key: 'Inomhus',
						data: inside_data.map((d) => ({ ...d, sensor: 'Inomhus' })),
						color: '#ff7f0e'
					}
				]}
				renderContext="svg"
				yDomain={[-5, 20]}
				legend
				props={{
					spline: { curve: curveCatmullRom }
				}}
			>
				{#snippet tooltip({ context, series })}
					{@const activeSeriesColor = series.find(
						(s) => s.key === context.tooltip.data?.sensor
					)?.color}
					<Tooltip.Root>
						{#snippet children({ data })}
							<Tooltip.Header>{format(context.x(data), PeriodType.DayTime)}</Tooltip.Header>
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
	{#await recordings_promise then recordings}
		<div class="grid grid-cols-1 gap-4 md:grid-cols-2">
			{#each recordings as recording}
				<VideoWithLoader
					class="w-full rounded-sm"
					src={recording.url}
					controls
					autoplay
					muted
					loop
				/>
			{/each}
		</div>
	{/await}
</div>
