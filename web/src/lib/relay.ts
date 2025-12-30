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
	const playlist_response = await authorizedRequest(
		user,
		PUBLIC_RELAY_URL,
		`${device_name}/start?bitrate=500000&framerate=24`
	);
	const playlist_endpoint = (await playlist_response.json()).playlist;
	return `${PUBLIC_RELAY_URL}${device_name}${playlist_endpoint}`;
};
