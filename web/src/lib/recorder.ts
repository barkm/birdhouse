import type { User } from 'firebase/auth';
import { authorizedRequest } from './request';
import { PUBLIC_RECORDER_URL } from '$env/static/public';
import type { Role } from './firebase';

export interface Recording {
	url: string;
	created_at: Date;
}

export const getRecordings = async (
	user: User,
	device_name: string,
	from?: Date,
	to?: Date
): Promise<Recording[]> => {
	let url_params = new URLSearchParams();
	if (from) {
		url_params.append('from', from.toISOString());
	}
	if (to) {
		url_params.append('to', to.toISOString());
	}
	const url = `recordings/${device_name}?${url_params.toString()}`;
	const response = await authorizedRequest(user, PUBLIC_RECORDER_URL, url);
	const data = await response.json();
	return data.map((entry: { url: string; created_at: string }) => ({
		url: entry.url,
		created_at: new Date(entry.created_at)
	}));
};

export interface SensorData {
	created_at: Date;
	temperature?: number;
	humidity?: number;
}

export const getSensorData = async (
	user: User,
	device_name: string,
	from?: Date,
	to?: Date
): Promise<SensorData[]> => {
	let url_params = new URLSearchParams();
	if (from) {
		url_params.append('from', from.toISOString());
	}
	if (to) {
		url_params.append('to', to.toISOString());
	}
	const url = `sensors/${device_name}?${url_params.toString()}`;
	const response = await authorizedRequest(user, PUBLIC_RECORDER_URL, url);
	const data = await response.json();
	return data.map((entry: { created_at: string; temperature: number; humidity: number }) => ({
		created_at: new Date(entry.created_at),
		temperature: entry.temperature,
		humidity: entry.humidity
	}));
};

export const listDevices = async (user: User): Promise<{ name: string; allowed_roles: Role[]; active: boolean }[]> => {
	const response = await authorizedRequest(user, PUBLIC_RECORDER_URL, 'list_devices');
	return response.json();
};

export const getStatus = async (user: User, device_name: string): Promise<{ status: string }> => {
	const { response } = await localRequestWithRelayFallback(user, device_name, `/status`);
	return response.json();
};

export const getCurrentSensorData = async (
	user: User,
	device_name: string
): Promise<SensorData> => {
	const { response } = await localRequestWithRelayFallback(user, device_name, `/sensor`);
	const sensor_data = await response.json();
	return {
		created_at: new Date(),
		temperature: sensor_data.temperature,
		humidity: sensor_data.humidity
	};
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

export const localRequestWithRelayFallback = async (
	user: User,
	device_name: string,
	endpoint: string
): Promise<{ response: Response; base_url: string }> => {
	const base_url = (await checkDeviceAvailability(device_name))
		? `https://${device_name}.local`
		: `${PUBLIC_RECORDER_URL}get/${device_name}`;
	const response = await authorizedRequest(user, base_url, endpoint);
	return { response, base_url };
};

export const checkDeviceAvailability = async (device_name: string): Promise<boolean> => {
	const url = `https://${device_name}.local/status`;
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
