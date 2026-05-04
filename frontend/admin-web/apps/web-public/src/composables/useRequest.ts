import axios from 'axios';

const API_BASE = import.meta.env.VITE_API_BASE_URL || '/api/v1';

const client = axios.create({ baseURL: API_BASE, timeout: 30000 });

// Response unwrap: backend returns { code: 2000, data: ..., msg: ... }
client.interceptors.response.use(
  (res) => {
    const body = res.data;
    if (body && typeof body === 'object' && 'code' in body && body.code === 2000) {
      return body.data ?? body;
    }
    return body;
  },
  (err) => {
    console.error('API error:', err?.response?.data || err.message);
    return Promise.reject(err);
  },
);

export function useRequest() {
  return {
    get: client.get.bind(client),
    post: client.post.bind(client) as typeof client.post,
  };
}
