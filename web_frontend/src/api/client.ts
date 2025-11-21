import axios, { AxiosInstance } from 'axios';

/**
 * API Client Configuration
 *
 * baseURL resolution order:
 * 1) VITE_API_URL (explicit override)
 * 2) VITE_QUERY_API_URL (legacy name)
 * 3) Current origin (empty string so relative paths work with Vite proxy)
 */
const API_BASE_URL =
  import.meta.env?.VITE_API_URL ??
  import.meta.env?.VITE_QUERY_API_URL ??
  '';

const client: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
});

/**
 * Request Interceptor
 * Adds X-Request-ID header for distributed tracing
 */
client.interceptors.request.use((config) => {
  const randomId =
    typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function'
      ? crypto.randomUUID()
      : Math.random().toString(36).slice(2);
  const requestId = sessionStorage.getItem('requestId') || randomId;
  sessionStorage.setItem('requestId', requestId);
  config.headers['X-Request-ID'] = requestId;
  return config;
});

/**
 * Response Interceptor
 * Logs errors for debugging
 */
client.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error('API Error:', {
      status: error.response?.status,
      data: error.response?.data,
      message: error.message,
    });
    return Promise.reject(error);
  }
);

export default client;
