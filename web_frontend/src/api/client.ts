import axios, { AxiosInstance } from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

const client: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor to add request ID header
client.interceptors.request.use((config) => {
  const requestId = sessionStorage.getItem('requestId') || crypto.randomUUID();
  sessionStorage.setItem('requestId', requestId);
  config.headers['X-Request-ID'] = requestId;
  return config;
});

// Response interceptor for error handling
client.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error('API Error:', error.response?.data || error.message);
    return Promise.reject(error);
  }
);

export default client;
