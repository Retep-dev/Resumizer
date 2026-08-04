import axios from 'axios';

const envUrl = import.meta.env.VITE_API_BASE_URL || import.meta.env.VITE_URL;
// In production (e.g. Vercel), fallback directly to the live Render backend URL
const defaultUrl = import.meta.env.DEV ? '' : 'https://resumizer-1stb.onrender.com';
const rawUrl = envUrl || defaultUrl;

const API_BASE_URL = rawUrl.replace(/\/+$/, '');

console.log('[Resumizer API] Connected to backend URL:', API_BASE_URL || '(Local Proxy)');

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 300000, // 5 minutes timeout for cloud deployment & cold starts
});

export default api;
