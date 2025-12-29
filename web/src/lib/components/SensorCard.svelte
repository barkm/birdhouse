<script lang="ts">

    interface Props {
        title: string;
        temperature: number;
        humidity: number;
    }

    const { temperature, title, humidity } : Props = $props()

    const getBackgroundStyle = (temp: number) => {
        if (temp <= -10) {
            return "bg-blue-300";
        }
        if (temp <= 0) {
            return "bg-blue-200";
        }
        if (temp <= 15) {
            return "bg-green-200";
        }
        if (temp <= 25) {
            return "bg-yellow-200";
        }
        if (temp <= 30) {
            return "bg-red-200";
        }
        return "bg-red-300";
    };

</script>


<div class="p-4 {getBackgroundStyle(temperature)} rounded-lg">
    <h2 class="text-xl font-semibold mb-2">{title}</h2>
    <p class="text-3xl">{temperature.toFixed(1)}°C</p>
    <p class="text-lg">Humidity: {humidity.toFixed(0)}%</p>
</div>