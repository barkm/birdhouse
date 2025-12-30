import type { User } from 'firebase/auth';
import { authorizedRequest } from './request';
import { PUBLIC_RELAY_URL } from '$env/static/public';

export interface SensorData {
	temperature: number;
	humidity: number;
}

export const getSensorData = async (user: User, device_name: string): Promise<SensorData> => {
	const sensor_response = await authorizedRequest(user, PUBLIC_RELAY_URL, `${device_name}/sensor`);
	return await sensor_response.json();
};

export const startAndGetStreamUrl = async (user: User, device_name: string): Promise<string> => {
	const base_url = (await checkDeviceAvailability(device_name))
		? `http://${device_name}.local:8000`
		: `${PUBLIC_RELAY_URL}${device_name}`;
	const playlist_response = await authorizedRequest(
		user,
		base_url,
		`/start?bitrate=500000&framerate=24`
	);
	const playlist_endpoint = (await playlist_response.json()).playlist;
	return `${base_url}${playlist_endpoint}`;
};

async function checkDeviceAvailability(device_name: string): Promise<boolean> {
	const url = `http://${device_name}.local:8000/status`;
	const controller = new AbortController();
	const timeoutId = setTimeout(() => controller.abort(), 2000);
	try {
		await fetch(url, {
			method: 'GET',
			signal: controller.signal
		});
		return true;
	} catch (error: any) {
		if (error.name !== 'AbortError') {
			console.log(`⚠️ ${url} is unreachable, but DNS might have resolved.`);
		}
		return false;
	} finally {
		clearTimeout(timeoutId);
	}
}
