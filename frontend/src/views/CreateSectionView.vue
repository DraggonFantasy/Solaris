<template>
  <div class="section-create-page">
    <RouterLink to="/sections" class="back-link">← {{ t('common.back') }}</RouterLink>
    <h1 class="page-title">{{ t('sections.newTitle') }}</h1>

    <form class="card section-form" @submit.prevent="createSection">
      <label class="form-group">
        <span>{{ t('sections.sectionName') }}</span>
        <input v-model.trim="form.name" type="text" required autofocus />
      </label>
      <label class="form-group">
        <span>{{ t('sections.sectionBrief') }}</span>
        <textarea v-model.trim="form.brief" rows="5" />
      </label>
      <div v-if="error" class="alert alert-error">{{ error }}</div>
      <footer class="form-actions">
        <button class="btn btn-primary" type="submit" :disabled="saving || !form.name">
          {{ saving ? t('common.loading') : t('common.save') }}
        </button>
        <RouterLink class="btn btn-outline" to="/sections">{{ t('common.cancel') }}</RouterLink>
      </footer>
    </form>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import api from '../api'

const { t } = useI18n()
const router = useRouter()
const form = ref({ name: '', brief: '' })
const saving = ref(false)
const error = ref('')

async function createSection() {
  saving.value = true
  error.value = ''
  try {
    const { data } = await api.post('/sections/', form.value)
    router.push({ name: 'section-detail', params: { slug: data.slug } })
  } catch (err) {
    error.value = err.response?.data?.detail || t('sections.createError')
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.section-create-page { max-width: 760px; margin: 0 auto; }
.back-link { color: var(--color-text-muted); display: inline-block; margin-bottom: 1rem; text-decoration: none; }
.section-form { padding: 1.5rem; }
.form-group > span { font-size: 0.875rem; font-weight: 600; }
.form-actions { display: flex; gap: 0.75rem; }
</style>
