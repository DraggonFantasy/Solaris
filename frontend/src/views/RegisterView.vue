<template>
  <div class="auth-page">
    <div class="auth-card card">
      <h1 class="auth-title">{{ t('auth.registerTitle') }}</h1>

      <div v-if="successMsg" class="alert alert-success">{{ successMsg }}</div>
      <div v-if="error" class="alert alert-error">{{ error }}</div>

      <form v-if="!successMsg" @submit.prevent="handleRegister">
        <div class="form-group">
          <label for="username">{{ t('auth.username') }}</label>
          <input id="username" v-model="form.username" type="text" required autocomplete="username" />
          <span v-if="fieldErrors.username" class="form-error">{{ fieldErrors.username }}</span>
        </div>

        <div class="form-row">
          <div class="form-group">
            <label for="firstName">{{ t('auth.firstName') }}</label>
            <input id="firstName" v-model="form.first_name" type="text" autocomplete="given-name" />
          </div>
          <div class="form-group">
            <label for="lastName">{{ t('auth.lastName') }}</label>
            <input id="lastName" v-model="form.last_name" type="text" autocomplete="family-name" />
          </div>
        </div>

        <div class="form-group">
          <label for="email">{{ t('auth.email') }}</label>
          <input id="email" v-model="form.email" type="email" autocomplete="email" />
        </div>

        <div class="form-group">
          <label for="password">{{ t('auth.password') }}</label>
          <input id="password" v-model="form.password" type="password" required autocomplete="new-password" />
          <span v-if="fieldErrors.password" class="form-error">{{ fieldErrors.password }}</span>
        </div>

        <div class="form-group">
          <label for="password2">{{ t('auth.password2') }}</label>
          <input id="password2" v-model="form.password2" type="password" required autocomplete="new-password" />
        </div>

        <button class="btn btn-primary full-width" type="submit" :disabled="loading">
          {{ loading ? t('common.loading') : t('auth.registerBtn') }}
        </button>
      </form>

      <p class="auth-switch">
        {{ t('auth.hasAccount') }}
        <RouterLink to="/login">{{ t('nav.login') }}</RouterLink>
      </p>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useAuthStore } from '../stores/auth'

const { t } = useI18n()
const auth = useAuthStore()

const form = ref({
  username: '', first_name: '', last_name: '',
  email: '', password: '', password2: ''
})
const error = ref('')
const fieldErrors = ref({})
const successMsg = ref('')
const loading = ref(false)

async function handleRegister() {
  error.value = ''
  fieldErrors.value = {}
  loading.value = true
  try {
    await auth.register(form.value)
    successMsg.value = t('auth.registerSuccess')
  } catch (err) {
    const data = err.response?.data
    if (data && typeof data === 'object') {
      fieldErrors.value = data
    } else {
      error.value = t('common.error')
    }
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
  max-width: 480px;
}

.auth-title {
  font-family: var(--font-serif);
  font-size: 1.5rem;
  margin-bottom: 1.5rem;
  color: var(--color-primary);
}

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
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
