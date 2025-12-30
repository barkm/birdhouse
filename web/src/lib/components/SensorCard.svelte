<script lang="ts">
	interface Props {
		title: string;
		temperature: number;
		temperature_limits?: {
			max: number;
			min: number;
		};
		humidity: number;
	}

	const { temperature, temperature_limits, title, humidity }: Props = $props();

	const getBackgroundStyle = (temp: number) => {
		if (temp <= -10) {
			return 'bg-blue-300';
		}
		if (temp <= 0) {
			return 'bg-blue-200';
		}
		if (temp <= 15) {
			return 'bg-green-200';
		}
		if (temp <= 25) {
			return 'bg-yellow-200';
		}
		if (temp <= 30) {
			return 'bg-red-200';
		}
		return 'bg-red-300';
	};
</script>

<div class="p-4 {getBackgroundStyle(temperature)} rounded-lg">
	<h2 class="mb-2 text-xl font-semibold">{title}</h2>
	<p class="text-3xl">{temperature.toFixed(1)}°C</p>
	{#if temperature_limits}
		<div class="flex flex-row space-x-2 text-xs text-gray-700">
			<span>max {temperature_limits.max.toFixed(1)}°C</span>
			<span>min {temperature_limits.min.toFixed(1)}°C</span>
		</div>
	{/if}
	<p class="text-lg">Humidity: {humidity.toFixed(0)}%</p>
</div>
