<template>
  <div>
    <RouterLink to="/sections" class="back-link">← {{ t('common.back') }}</RouterLink>
    <header class="archive-header">
      <div>
        <h1 class="page-title">{{ t('archive.title') }}</h1>
        <p>{{ t('archive.description') }}</p>
      </div>
    </header>

    <div v-if="loading" class="text-muted">{{ t('common.loading') }}</div>
    <div v-else-if="error" class="alert alert-error">{{ error }}</div>
    <div v-else-if="!dialogues.length" class="card empty-state">{{ t('archive.empty') }}</div>
    <div v-else class="archive-list">
      <article v-for="dialogue in dialogues" :key="dialogue.id" class="card archive-row">
        <div>
          <span class="section-name">{{ dialogue.section_name }}</span>
          <RouterLink :to="`/dialogues/${dialogue.id}`" class="dialogue-title">
            {{ dialogue.title }}
          </RouterLink>
          <p v-if="dialogue.summary">{{ dialogue.summary }}</p>
        </div>
        <div class="archive-actions">
          <button class="btn btn-primary btn-sm" :disabled="savingId === dialogue.id" @click="restore(dialogue)">
            {{ t('archive.restore') }}
          </button>
          <button class="btn btn-danger btn-sm" :disabled="savingId === dialogue.id" @click="remove(dialogue)">
            {{ t('archive.delete') }}
          </button>
        </div>
      </article>
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import api from '../api'

const { t } = useI18n()
const dialogues = ref([])
const loading = ref(true)
const savingId = ref(null)
const error = ref('')

onMounted(loadArchive)

async function loadArchive() {
  try {
    const { data } = await api.get('/dialogues/review/', { params: { status: 'archived' } })
    dialogues.value = data.results || data
  } catch {
    error.value = t('common.error')
  } finally {
    loading.value = false
  }
}

async function restore(dialogue) {
  savingId.value = dialogue.id
  try {
    await api.post(`/dialogues/${dialogue.id}/moderate/`, { status: 'published' })
    dialogues.value = dialogues.value.filter((item) => item.id !== dialogue.id)
  } finally {
    savingId.value = null
  }
}

async function remove(dialogue) {
  if (!window.confirm(t('archive.deleteConfirm'))) return
  savingId.value = dialogue.id
  try {
    await api.delete(`/dialogues/${dialogue.id}/`)
    dialogues.value = dialogues.value.filter((item) => item.id !== dialogue.id)
  } finally {
    savingId.value = null
  }
}
</script>

<style scoped>
.back-link { color: var(--color-text-muted); display: inline-block; margin-bottom: 1rem; text-decoration: none; }
.archive-header { margin-bottom: 1.5rem; }
.archive-header .page-title { margin-bottom: 0.4rem; }
.archive-header p, .archive-row p { color: var(--color-text-muted); }
.archive-list { display: flex; flex-direction: column; gap: 1rem; }
.archive-row { align-items: flex-start; display: flex; gap: 1rem; justify-content: space-between; }
.archive-row > div:first-child { min-width: 0; }
.section-name { color: var(--color-accent); display: block; font-size: 0.72rem; font-weight: 600; text-transform: uppercase; }
.dialogue-title { color: var(--color-primary); display: inline-block; font-family: var(--font-serif); font-weight: 700; margin: 0.25rem 0; text-decoration: none; }
.archive-actions { display: flex; flex: 0 0 auto; gap: 0.5rem; }
.empty-state { color: var(--color-text-muted); }
@media (max-width: 620px) { .archive-row { flex-direction: column; } }
</style>
