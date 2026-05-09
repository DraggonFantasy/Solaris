<template>
  <div>
    <div class="page-header">
      <h1 class="page-title">{{ t('dialogue.myDialogues') }}</h1>
      <RouterLink class="btn btn-primary" to="/dialogues/create">
        + {{ t('dialogue.createBtn') }}
      </RouterLink>
    </div>

    <div v-if="loading" class="text-muted">{{ t('common.loading') }}</div>

    <div v-else-if="dialogues.length === 0" class="empty-state card">
      <p>{{ t('dialogue.noOwn') }}</p>
      <RouterLink class="btn btn-primary" to="/dialogues/create">
        {{ t('dialogue.createBtn') }}
      </RouterLink>
    </div>

    <div v-else class="dialogue-list">
      <RouterLink v-for="d in dialogues" :key="d.id" :to="`/dialogues/${d.id}`" class="dialogue-row">
        <div class="dialogue-main">
          <div class="dialogue-title-line">
            <span class="dialogue-title">{{ d.title }}</span>
            <span class="dialogue-status" :class="d.status">{{ statusLabel(d.status) }}</span>
          </div>
          <p v-if="d.moderation_note" class="moderation-note">
            {{ d.moderation_note }}
          </p>
          <div class="dialogue-subline">
            <span>{{ d.section_name }}</span>
            <span>{{ formatDate(d.created_at) }}</span>
            <span v-if="authorLine(d)">{{ authorLine(d) }}</span>
            <span v-if="d.status === 'published'">♥ {{ d.likes_count }}</span>
          </div>
          <p v-if="d.summary" class="dialogue-summary">{{ d.summary }}</p>
        </div>
      </RouterLink>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import api from '../api'

const { t } = useI18n()
const dialogues = ref([])
const loading = ref(true)

onMounted(async () => {
  try {
    const { data } = await api.get('/dialogues/mine/')
    dialogues.value = data.results || data
  } finally {
    loading.value = false
  }
})

function formatDate(iso) {
  return new Date(iso).toLocaleDateString()
}

function statusLabel(status) {
  return t(`dialogue.status.${status || 'draft'}`)
}

function authorLine(dialogue) {
  const authors = (dialogue.authors || []).map((author) => author.name).filter(Boolean)
  if (authors.length) return authors.join(', ')
  return [dialogue.human_author_username, dialogue.llm_name].filter(Boolean).join(', ')
}
</script>

<style scoped>
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.5rem;
}

.page-header .page-title {
  margin-bottom: 0;
}

.empty-state {
  text-align: center;
  padding: 3rem;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1rem;
  color: var(--color-text-muted);
}

.dialogue-list {
  border-bottom: 1px solid var(--color-border);
  border-top: 1px solid var(--color-border);
}

.dialogue-row {
  color: inherit;
  display: flex;
  padding: 0.9rem 0.25rem;
  text-decoration: none;
  transition: background 0.15s;
}

.dialogue-row + .dialogue-row {
  border-top: 1px solid var(--color-border);
}

.dialogue-row:hover {
  background: var(--color-bg);
}

.dialogue-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
  min-width: 0;
}

.dialogue-title-line {
  align-items: center;
  display: flex;
  gap: 0.75rem;
  justify-content: space-between;
}

.dialogue-title {
  font-family: var(--font-serif);
  font-weight: 700;
  color: var(--color-text);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.dialogue-row:hover .dialogue-title {
  color: var(--color-primary);
}

.dialogue-subline {
  color: var(--color-text-muted);
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem 0.9rem;
  font-size: 0.8rem;
}

.dialogue-summary {
  color: var(--color-text-muted);
  display: -webkit-box;
  font-size: 0.85rem;
  line-height: 1.45;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.dialogue-status {
  flex: 0 0 auto;
  font-size: 0.7rem;
  font-weight: 600;
  padding: 0.15rem 0.5rem;
  border-radius: 999px;
  white-space: nowrap;
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
  border-left: 3px solid #fde68a;
  color: #713f12;
  font-size: 0.82rem;
  line-height: 1.45;
  margin-top: 0.35rem;
  padding-left: 0.65rem;
}
</style>
