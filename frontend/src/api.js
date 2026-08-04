import axios from 'axios';

const rawUrl = import.meta.env.VITE_API_BASE_URL || '';
const API_BASE_URL = rawUrl.replace(/\/+$/, '');

const api = axios.create({
  baseURL: API_BASE_URL,
});

export default api;
