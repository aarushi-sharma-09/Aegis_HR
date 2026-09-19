import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  headers: { 'Content-Type': 'application/json' },
})

// ─── Documents ────────────────────────────────────────────────────────────────

export const uploadDocument = (formData) =>
  api.post('/documents/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })

export const fallbackUpload = (documentId, formData) =>
  api.post(`/documents/fallback-upload/${documentId}`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })

// ─── Admin ────────────────────────────────────────────────────────────────────

export const getReviewQueue = () => api.get('/admin/review-queue')

export const getReviewDetail = (threadId) => api.get(`/admin/review/${threadId}`)

export const resolveReview = (threadId, decision, notes = '') =>
  api.post(`/admin/review/${threadId}/resolve`, { decision, notes })

export const getDashboardStats = () => api.get('/admin/dashboard/stats')

export const getApplicants = () => api.get('/admin/applicants')

export const createApplicant = (data) => api.post('/admin/applicants', data)

export default api
