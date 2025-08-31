<script lang="ts">
  import { PUBLIC_RELAY_URL } from '$env/static/public';
	import Video from '$lib/Video.svelte';

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

  let isLoading = $state(true);

</script>

<column>
{#await device_playlists_promise then device_playlists}
  {#each device_playlists as device_playlist}
    <stream class:loading={isLoading}>
     <Video 
      src={`${PUBLIC_RELAY_URL}${device_playlist.device.name}${device_playlist.playlist.path}`}
      controls
      autoplay
      muted
      playsinline
      onplaying={() => {
        isLoading = false;
      }}
      />
    </stream>
  {/each}
{/await}
</column>

<style>
  column {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 1rem;
    padding: 1rem;
  }

  stream {
    width: 50%;
    aspect-ratio: 16 / 9;
    transition: opacity 1000ms ease-in-out;
  }

  stream.loading {
    opacity: 0.0;
  }

  stream :global(video) {
    width: 100%;
    height: 100%;
  }

</style>