<script lang="ts">
  import HLSPlayer from '$lib/HLSPlayer.svelte';
  import { PUBLIC_RELAY_URL } from '$env/static/public';

  interface Device {
    name: string;
  }

  interface Playlist {
    path: string;
  }

  const fetch_devices = async (): Promise<Device[]> => {
    const device_response = await fetch(`${PUBLIC_RELAY_URL}list`);
    return await device_response.json();
  };

  const fetch_device_playlists = async (device: Device): Promise<{device: Device, playlist: Playlist}> => {
    const playlist_response = await fetch(`${PUBLIC_RELAY_URL}${device.name}/start`);
    const data = await playlist_response.json();
    return {
      device,
      playlist: {
        path: data.playlist
      }
    }
  };

  const devices_promise = fetch_devices();
  const device_playlists_promise = $derived(devices_promise.then(devices => Promise.all(devices.map(fetch_device_playlists))))

</script>

{#await device_playlists_promise then device_playlists}
  {#each device_playlists as device_playlist}
    {device_playlist.device.name}
    <HLSPlayer src={`${PUBLIC_RELAY_URL}${device_playlist.device.name}${device_playlist.playlist.path}`} />
  {/each}
{/await}
