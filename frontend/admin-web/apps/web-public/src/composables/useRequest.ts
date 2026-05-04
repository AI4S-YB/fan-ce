import axios from 'axios';

const API_BASE = import.meta.env.VITE_API_BASE_URL || '/api/v1';

const client = axios.create({ baseURL: API_BASE, timeout: 30000 });

// Response unwrap: backend returns { code: 2000, data: ..., msg: ... }
client.interceptors.response.use(
  (res) => {
    const body = res.data;
    if (body && typeof body === 'object' && 'code' in body && body.code === 2000) {
      // Return the unwrapped data directly (not wrapped in AxiosResponse)
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
  async function get<T = any>(url: string, params?: any): Promise<T> {
    const res: any = await client.get(url, { params });
    return res as T;
  }
  async function post<T = any>(url: string, data?: any): Promise<T> {
    const res: any = await client.post(url, data);
    return res as T;
  }
  return { get, post };
}
