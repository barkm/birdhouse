import type { User } from "firebase/auth";
import { authorizedRequest } from "./request";
import { PUBLIC_RECORDER_URL } from "$env/static/public";


export interface Recording {
    url: string;
    created_at: Date;
}


export const getRecordings = async (user: User, device_name: string, from?: Date, to?: Date): Promise<Recording[]> => {
    let url_params = new URLSearchParams();
    if (from) {
        url_params.append('from', from.toISOString());
    }
    if (to) {
        url_params.append('to', to.toISOString());
    }
    const url = `recordings/${device_name}?${url_params.toString()}`;
    const response = await authorizedRequest(
        user,
        PUBLIC_RECORDER_URL,
        url
    );
    const data = await response.json();
    return data.map((entry: { url: string; created_at: string }) => ({
        url: entry.url,
        created_at: new Date(entry.created_at)
    }));
}

export interface SensorData {
    created_at: Date;
    temperature: number;
    humidity: number;
}

export const getSensorData = async (user: User, device_name: string, from?: Date, to?: Date): Promise<SensorData[]> => {
    let url_params = new URLSearchParams();
    if (from) {
        url_params.append('from', from.toISOString());
    }
    if (to) {
        url_params.append('to', to.toISOString());
    }
    const url = `sensors/${device_name}?${url_params.toString()}`;
    const response = await authorizedRequest(
        user,
        PUBLIC_RECORDER_URL,
        url
    );
    const data = await response.json();
    return data.map((entry: { created_at: string; temperature: number; humidity: number }) => ({
        created_at: new Date(entry.created_at),
        temperature: entry.temperature,
        humidity: entry.humidity
    }));
}

	// const fetch_recordings = async (device: Device): Promise<Recording[]> => {
	// 	if (!$user) {
	// 		return [];
	// 	}
	// 	const recordings_response = await authorizedRequest(
	// 		$user,
	// 		PUBLIC_RECORDER_URL,
	// 		`recordings/${device.name}`
	// 	);
	// 	return await recordings_response.json();
	// };

    // const fetchTemperatures = async (device_name: string): Promise<TemperatureData[]> => {
	// 	if (!$user) return [];
    //     const response = await authorizedRequest($user, PUBLIC_RECORDER_URL, `sensors/${device_name}`)
    //     const parsedResponse = await response.json();
    //     return parsedResponse.map((entry: { created_at: string; temperature: number }) => ({ created_at: new Date(entry.created_at), temperature: entry.temperature }));
    // };