const isServer = typeof window === 'undefined';
const defaultApiUrl = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";
const serverApiUrl = process.env.NEXT_INTERNAL_API_URL || defaultApiUrl;

export const API_URL = `${isServer ? serverApiUrl : defaultApiUrl}/api/v1`;
