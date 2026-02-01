import { PUBLIC_DEVICE_NAMES } from '$env/static/public';

export async function entries() {
  const names: string[] = JSON.parse(PUBLIC_DEVICE_NAMES);
  return names.map((name) => ({ name }));
}