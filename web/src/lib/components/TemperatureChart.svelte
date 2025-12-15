<script lang="ts">
	import { PUBLIC_RECORDER_URL } from "$env/static/public";
	import { LineChart } from "layerchart";
	import { user } from "$lib/firebase";
	import { authorizedRequest } from "$lib/request";


	interface Device {
		name: string;
	}

    interface TemperatureData {
        created_at: Date;
        temperature: number;
    }

	const props: { devices: Device[] } = $props();

    const colors = [
        "#1f77b4",
        "#ff7f0e",
        "#2ca02c",
        "#d62728",
        "#9467bd",
        "#8c564b",
        "#e377c2",
        "#7f7f7f",
        "#bcbd22",
        "#17becf"
    ];

    const fetchTemperatures = async (device_name: string): Promise<TemperatureData[]> => {
		if (!$user) return [];
        const response = await authorizedRequest($user, PUBLIC_RECORDER_URL, `sensors/${device_name}`)
        const parsedResponse = await response.json();
        return parsedResponse.map((entry: { created_at: string; temperature: number }) => ({ created_at: new Date(entry.created_at), temperature: entry.temperature }));
    };

    const temperatures_promise = $derived(
        Promise.all(
            props.devices.map(async (device) => {
                const temps = await fetchTemperatures(device.name);
                return { device, temperatures: temps };
            })
        )
    );

</script>

{#await temperatures_promise then device_temps}
    <div class="h-[300px] w-3/4 p-4 border rounded-sm">
    <LineChart
        x="created_at"
        y="temperature"
        series={device_temps.map((dt, index) => ({
            key: dt.device.name === "house" ? "Inomhus" : dt.device.name === "birdhouse" ? "Utomhus" : dt.device.name,
            data: dt.temperatures,
            color: colors[index % colors.length]
        }))}
        renderContext="svg"
        yDomain={[-5, 20]}
        legend
    />
    </div>
{/await}