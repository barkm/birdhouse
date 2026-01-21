import { PUBLIC_FIREBASE_API_KEY, PUBLIC_FIREBASE_AUTH_DOMAIN } from '$env/static/public';
import { initializeApp } from 'firebase/app';
import {
	getAuth,
	onAuthStateChanged,
	GoogleAuthProvider,
	signInWithPopup,
	signOut,
	type User
} from 'firebase/auth';
import { writable } from 'svelte/store';

export enum Role {
	ADMIN = 'admin',
	USER = 'user'
}

const firebaseConfig = {
	apiKey: PUBLIC_FIREBASE_API_KEY,
	authDomain: PUBLIC_FIREBASE_AUTH_DOMAIN
};

const app = initializeApp(firebaseConfig);

export const auth = getAuth(app);
export const user = writable<User | null>(null);
export const isLoading = writable(true);
onAuthStateChanged(auth, (u: User | null) => {
	user.set(u);
	isLoading.set(false);
});

export const loginWithGoogle = () => signInWithPopup(auth, new GoogleAuthProvider());
export const logout = () => signOut(auth);


