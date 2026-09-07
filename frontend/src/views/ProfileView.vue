<template>
  <div class="profile-page">
    <h1 class="page-title">{{ auth.user?.username }}</h1>

    <div v-if="saved" class="alert alert-success">{{ t('profile.saved') }}</div>

    <div class="profile-grid">
      <div class="card">
        <h2 class="card-title">{{ t('nav.profile') }}</h2>
        <form @submit.prevent="saveProfile">
          <div class="form-group">
            <label>{{ t('auth.firstName') }}</label>
            <input v-model="form.first_name" type="text" />
          </div>
          <div class="form-group">
            <label>{{ t('auth.lastName') }}</label>
            <input v-model="form.last_name" type="text" />
          </div>
          <div class="form-group">
            <label>{{ t('auth.email') }}</label>
            <input v-model="form.email" type="email" />
          </div>
          <div class="form-group">
            <label>{{ t('profile.bio') }}</label>
            <input v-model="form.bio" type="text" maxlength="32" />
            <small>{{ t('profile.bioHint') }}</small>
          </div>
          <button class="btn btn-primary" type="submit">{{ t('common.save') }}</button>
        </form>
      </div>

      <div class="card stats-card">
        <h2 class="card-title">{{ t('profile.usage') }}</h2>
        <div class="stat-row">
          <span>{{ t('profile.tokensUsed') }}</span>
          <strong>{{ auth.user?.tokens_used }}</strong>
        </div>
        <div class="stat-row">
          <span>{{ t('profile.budget') }}</span>
          <strong>{{ auth.user?.token_budget === 0 ? t('profile.unlimited') : auth.user?.token_budget }}</strong>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useAuthStore } from '../stores/auth'
import api from '../api'

const { t } = useI18n()
const auth = useAuthStore()
const saved = ref(false)

const form = ref({
  first_name: auth.user?.first_name || '',
  last_name: auth.user?.last_name || '',
  email: auth.user?.email || '',
  bio: auth.user?.bio || '',
})

onMounted(async () => {
  if (!auth.user) await auth.fetchMe()
  form.value = {
    first_name: auth.user?.first_name || '',
    last_name: auth.user?.last_name || '',
    email: auth.user?.email || '',
    bio: auth.user?.bio || '',
  }
})

async function saveProfile() {
  await api.patch('/auth/me/', form.value)
  await auth.fetchMe()
  saved.value = true
  setTimeout(() => { saved.value = false }, 3000)
}
</script>

<style scoped>
.profile-grid {
  display: grid;
  grid-template-columns: 2fr 1fr;
  gap: 1.5rem;
  align-items: start;
}

.card-title {
  font-family: var(--font-serif);
  font-size: 1.125rem;
  margin-bottom: 1.25rem;
  color: var(--color-primary);
}

.stats-card {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.stat-row {
  display: flex;
  justify-content: space-between;
  font-size: 0.9rem;
  padding: 0.5rem 0;
  border-bottom: 1px solid var(--color-border);
}
</style>
