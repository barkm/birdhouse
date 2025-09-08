import type { User } from 'firebase/auth';

export const authorizedRequest = async (user: User, base_url: string, endpoint: string) => {
	const id_token = await user.getIdToken();
	if (!id_token) {
		throw new Error('User is not authenticated');
	}
	const url = `${base_url}${endpoint}`;
	return fetch(url, {
		method: 'GET',
		headers: {
			Authorization: `Bearer ${id_token}`
		}
	});
};
