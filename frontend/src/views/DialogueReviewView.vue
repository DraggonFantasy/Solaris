<template>
  <div>
    <div class="page-header">
      <h1 class="page-title">{{ t('moderation.title') }}</h1>
      <select v-model="statusFilter" class="status-filter" @change="loadDialogues">
        <option value="">{{ t('moderation.all') }}</option>
        <option value="submitted">{{ t('dialogue.status.submitted') }}</option>
        <option value="changes_requested">{{ t('dialogue.status.changes_requested') }}</option>
        <option value="rejected">{{ t('dialogue.status.rejected') }}</option>
        <option value="published">{{ t('dialogue.status.published') }}</option>
        <option value="archived">{{ t('dialogue.status.archived') }}</option>
      </select>
    </div>

    <div v-if="!auth.isStaff" class="alert alert-error">{{ t('moderation.staffOnly') }}</div>
    <div v-else-if="loading" class="text-muted">{{ t('common.loading') }}</div>
    <div v-else-if="dialogues.length === 0" class="empty-state card">{{ t('moderation.empty') }}</div>

    <div v-else class="review-list">
      <article v-for="dialogue in dialogues" :key="dialogue.id" class="review-row card">
        <div class="review-main">
          <div class="dialogue-section-tag">{{ dialogue.section_name }}</div>
          <RouterLink :to="`/dialogues/${dialogue.id}`" class="review-title">
            {{ dialogue.title }}
          </RouterLink>
          <p v-if="dialogue.summary" class="review-summary">{{ dialogue.summary }}</p>
          <div class="review-meta">
            <span>{{ dialogue.human_author_username || t('moderation.unknownAuthor') }}</span>
            <span>{{ formatDate(dialogue.created_at) }}</span>
            <span class="dialogue-status" :class="dialogue.status">{{ t(`dialogue.status.${dialogue.status}`) }}</span>
          </div>
          <p v-if="dialogue.moderation_note" class="moderation-note">{{ dialogue.moderation_note }}</p>
        </div>

        <form class="review-actions" @submit.prevent="moderate(dialogue)">
          <select v-model="dialogue.nextStatus">
            <option value="published">{{ t('moderation.publish') }}</option>
            <option value="changes_requested">{{ t('moderation.requestChanges') }}</option>
            <option value="rejected">{{ t('moderation.reject') }}</option>
            <option value="archived">{{ t('moderation.archive') }}</option>
          </select>
          <textarea
            v-model="dialogue.nextNote"
            rows="3"
            :placeholder="t('moderation.notePlaceholder')"
          />
          <button class="btn btn-primary btn-sm" type="submit" :disabled="savingId === dialogue.id">
            {{ savingId === dialogue.id ? t('common.loading') : t('common.save') }}
          </button>
        </form>
      </article>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useAuthStore } from '../stores/auth'
import api from '../api'

const { t } = useI18n()
const auth = useAuthStore()
const dialogues = ref([])
const loading = ref(true)
const savingId = ref(null)
const statusFilter = ref('submitted')

onMounted(loadDialogues)

async function loadDialogues() {
  if (!auth.isStaff) {
    loading.value = false
    return
  }
  loading.value = true
  try {
    const params = statusFilter.value ? { status: statusFilter.value } : {}
    const { data } = await api.get('/dialogues/review/', { params })
    dialogues.value = (data.results || data).map((dialogue) => ({
      ...dialogue,
      nextStatus: dialogue.status === 'published' ? 'archived' : 'published',
      nextNote: dialogue.moderation_note || '',
    }))
  } finally {
    loading.value = false
  }
}

async function moderate(dialogue) {
  savingId.value = dialogue.id
  try {
    const { data } = await api.post(`/dialogues/${dialogue.id}/moderate/`, {
      status: dialogue.nextStatus,
      moderation_note: dialogue.nextNote,
    })
    dialogue.status = data.status
    dialogue.moderation_note = data.moderation_note
    if (statusFilter.value && data.status !== statusFilter.value) {
      dialogues.value = dialogues.value.filter((item) => item.id !== dialogue.id)
    }
  } finally {
    savingId.value = null
  }
}

function formatDate(iso) {
  return new Date(iso).toLocaleDateString()
}
</script>

<style scoped>
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 1rem;
  margin-bottom: 1.5rem;
}

.page-header .page-title {
  margin-bottom: 0;
}

.status-filter {
  min-width: 220px;
}

.empty-state {
  padding: 2rem;
  color: var(--color-text-muted);
}

.review-list {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.review-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 280px;
  gap: 1.25rem;
}

.review-main {
  min-width: 0;
}

.dialogue-section-tag {
  font-size: 0.7rem;
  font-weight: 600;
  color: var(--color-accent);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin-bottom: 0.35rem;
}

.review-title {
  font-family: var(--font-serif);
  font-weight: 700;
  color: var(--color-text);
  text-decoration: none;
}

.review-title:hover {
  color: var(--color-primary);
}

.review-summary {
  color: var(--color-text-muted);
  font-size: 0.9rem;
  line-height: 1.5;
  margin-top: 0.5rem;
}

.review-meta {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 0.75rem;
  margin-top: 0.75rem;
  color: var(--color-text-muted);
  font-size: 0.8rem;
}

.dialogue-status {
  display: inline-block;
  font-size: 0.7rem;
  font-weight: 600;
  padding: 0.15rem 0.5rem;
  border-radius: 999px;
}

.dialogue-status.published {
  background: #dcfce7;
  color: #166534;
}

.dialogue-status.draft {
  background: #f1f5f9;
  color: #475569;
}

.dialogue-status.submitted {
  background: #dbeafe;
  color: #1d4ed8;
}

.dialogue-status.changes_requested {
  background: #fef9c3;
  color: #854d0e;
}

.dialogue-status.rejected {
  background: #fee2e2;
  color: #991b1b;
}

.dialogue-status.archived {
  background: #ede9fe;
  color: #5b21b6;
}

.moderation-note {
  border-left: 3px solid var(--color-border);
  color: var(--color-text-muted);
  font-size: 0.875rem;
  margin-top: 0.75rem;
  padding-left: 0.75rem;
}

.review-actions {
  display: flex;
  flex-direction: column;
  gap: 0.6rem;
}

.review-actions textarea {
  resize: vertical;
}

@media (max-width: 760px) {
  .page-header {
    align-items: stretch;
    flex-direction: column;
  }

  .review-row {
    grid-template-columns: 1fr;
  }
}
</style>
