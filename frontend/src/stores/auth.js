import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api from '../api'

export const useAuthStore = defineStore('auth', () => {
  const user = ref(null)
  const accessToken = ref(localStorage.getItem('access_token'))
  const refreshToken = ref(localStorage.getItem('refresh_token'))

  const isAuthenticated = computed(() => !!accessToken.value)
  const isStaff = computed(() => user.value?.is_staff || false)

  async function login(username, password) {
    const { data } = await api.post('/auth/login/', { username, password })
    accessToken.value = data.access
    refreshToken.value = data.refresh
    localStorage.setItem('access_token', data.access)
    localStorage.setItem('refresh_token', data.refresh)
    await fetchMe()
  }

  async function register(payload) {
    await api.post('/auth/register/', payload)
  }

  async function logout() {
    try {
      await api.post('/auth/logout/', { refresh: refreshToken.value })
    } catch {
      // ignore errors on logout
    }
    accessToken.value = null
    refreshToken.value = null
    user.value = null
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
  }

  async function fetchMe() {
    try {
      const { data } = await api.get('/auth/me/')
      user.value = data
    } catch {
      user.value = null
    }
  }

  if (accessToken.value) {
    fetchMe()
  }

  return { user, isAuthenticated, isStaff, login, register, logout, fetchMe }
})
