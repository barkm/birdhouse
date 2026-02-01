<script lang="ts">
	import type { User } from "firebase/auth";
	import RecordingsGrid from "./RecordingsGrid.svelte";

    interface Props {
        user: User;
        name: string;
    }

    const { user, name }: Props = $props();
</script>


<RecordingsGrid {user} device_name={name} />

