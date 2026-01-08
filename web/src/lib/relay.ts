import type { User } from 'firebase/auth';
import { authorizedRequest } from './request';
import { PUBLIC_RELAY_URL } from '$env/static/public';

export interface SensorData {
	temperature?: number;
	humidity?: number;
}

export const listDevices = async (user: User): Promise<{name: string}[]> => {
	const response = await authorizedRequest(user, PUBLIC_RELAY_URL, `list`);
	return response.json();
}

export const getStatus = async (user: User, device_name: string): Promise<{status: string}> => {
	const { response } = await localRequestWithRelayFallback(user, device_name, `/status`);
	return response.json();
}

export const getSensorData = async (user: User, device_name: string): Promise<SensorData> => {
	const { response } = await localRequestWithRelayFallback(user, device_name, `/sensor`);
	return await response.json();
};

export const startAndGetStreamUrl = async (user: User, device_name: string): Promise<string> => {
	const { response, base_url } = await localRequestWithRelayFallback(
		user,
		device_name,
		`/start?bitrate=500000&framerate=24`
	);
	const playlist_endpoint = (await response.json()).playlist;
	return `${base_url}${playlist_endpoint}`;
};

const localRequestWithRelayFallback = async (
	user: User,
	device_name: string,
	endpoint: string
): Promise<{ response: Response; base_url: string }> => {
	const base_url = (await checkDeviceAvailability(device_name))
		? `http://${device_name}.local:8000`
		: `${PUBLIC_RELAY_URL}${device_name}`;
	const response = await authorizedRequest(user, base_url, endpoint);
	return { response, base_url };
};

const checkDeviceAvailability = async (device_name: string): Promise<boolean> => {
	const url = `http://${device_name}.local:8000/status`;
	const controller = new AbortController();
	const timeoutId = setTimeout(() => controller.abort(), 500);
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
};
