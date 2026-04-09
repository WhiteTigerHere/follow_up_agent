import axios from 'axios';

const API_URL = 'http://localhost:8000/followups'; // Fast API default
const AUTH_URL = 'http://localhost:8000/auth';

axios.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export const login = (username, password) => {
  const formData = new URLSearchParams();
  formData.append('username', username);
  formData.append('password', password);
  return axios.post(`${AUTH_URL}/login`, formData, {
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded'
    }
  });
};

export const register = (email, password) => axios.post(`${AUTH_URL}/register`, { email, password });
export const getGoogleAuthUrl = () => axios.get(`${AUTH_URL}/login/google`);


export const getPending = () => axios.get(`${API_URL}/pending`);
export const getOverdue = () => axios.get(`${API_URL}/overdue`);
export const getReport = () => axios.get(`${API_URL}/report`);
export const createFollowUp = (data) => axios.post(`${API_URL}/create`, data);
export const approveFollowUp = (id) => axios.post(`${API_URL}/${id}/approve`);
export const rejectFollowUp = (id) => axios.post(`${API_URL}/${id}/reject`);
export const modifyFollowUp = (id, new_text) => axios.post(`${API_URL}/${id}/modify`, { new_text });
export const closeFollowUp = (id) => axios.post(`${API_URL}/${id}/close`);
export const explainFollowUp = (id) => axios.get(`${API_URL}/${id}/explain`);
export const getActive = () => axios.get(`${API_URL}/active`);
export const rescheduleFollowUp = (id, new_time) => axios.post(`${API_URL}/${id}/reschedule`, { new_time });
export const importGmailThread = (threadId) => axios.post(`http://localhost:8000/ingest/gmail_thread/${threadId}`);
