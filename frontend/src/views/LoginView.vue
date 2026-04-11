<template>
  <div class="auth-page">
    <div class="auth-card card">
      <h1 class="auth-title">{{ t('auth.loginTitle') }}</h1>

      <div v-if="error" class="alert alert-error">{{ error }}</div>

      <form @submit.prevent="handleLogin">
        <div class="form-group">
          <label for="username">{{ t('auth.username') }}</label>
          <input
            id="username"
            v-model="form.username"
            type="text"
            required
            autocomplete="username"
          />
        </div>

        <div class="form-group">
          <label for="password">{{ t('auth.password') }}</label>
          <input
            id="password"
            v-model="form.password"
            type="password"
            required
            autocomplete="current-password"
          />
        </div>

        <button class="btn btn-primary full-width" type="submit" :disabled="loading">
          {{ loading ? t('common.loading') : t('auth.loginBtn') }}
        </button>
      </form>

      <p class="auth-switch">
        {{ t('auth.noAccount') }}
        <RouterLink to="/register">{{ t('nav.register') }}</RouterLink>
      </p>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useAuthStore } from '../stores/auth'

const { t } = useI18n()
const auth = useAuthStore()
const router = useRouter()
const route = useRoute()

const form = ref({ username: '', password: '' })
const error = ref('')
const loading = ref(false)

async function handleLogin() {
  error.value = ''
  loading.value = true
  try {
    await auth.login(form.value.username, form.value.password)
    const redirect = route.query.redirect || '/'
    router.push(redirect)
  } catch {
    error.value = t('auth.loginError')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.auth-page {
  display: flex;
  justify-content: center;
  padding-top: 3rem;
}

.auth-card {
  width: 100%;
  max-width: 420px;
}

.auth-title {
  font-family: var(--font-serif);
  font-size: 1.5rem;
  margin-bottom: 1.5rem;
  color: var(--color-primary);
}

.full-width {
  width: 100%;
  justify-content: center;
}

.auth-switch {
  margin-top: 1.25rem;
  text-align: center;
  font-size: 0.9rem;
  color: var(--color-text-muted);
}

.auth-switch a {
  color: var(--color-primary);
  font-weight: 500;
}
</style>
