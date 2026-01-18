import type { User } from 'firebase/auth';

export const authorizedRequest = async (user: User, base_url: string, endpoint: string, method: string = 'GET', body?: any, headers?: Record<string, string>) => {
	const id_token = await user.getIdToken();
	if (!id_token) {
		throw new Error('User is not authenticated');
	}
	const url = `${base_url}${endpoint}`;
	return fetch(url, {
		method: method,
		headers: {
			Authorization: `Bearer ${id_token}`,
			...headers
		},
		body: body ? JSON.stringify(body) : undefined
	});
};
