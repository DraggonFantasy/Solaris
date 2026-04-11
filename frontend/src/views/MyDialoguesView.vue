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
      <div v-for="d in dialogues" :key="d.id" class="dialogue-row card">
        <div class="dialogue-row-main">
          <div class="dialogue-section-tag">{{ d.section_name }}</div>
          <RouterLink :to="`/dialogues/${d.id}`" class="dialogue-row-title">
            {{ d.title }}
          </RouterLink>
          <div class="dialogue-status" :class="d.published ? 'published' : 'draft'">
            {{ d.published ? t('dialogue.published') : t('dialogue.pendingReview') }}
          </div>
        </div>
        <div class="dialogue-row-meta">
          <span>{{ formatDate(d.created_at) }}</span>
          <span v-if="d.llm_name">{{ d.llm_name }}</span>
          <span>♥ {{ d.likes_count }}</span>
        </div>
      </div>
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
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.dialogue-row {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 1rem;
}

.dialogue-row-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
}

.dialogue-section-tag {
  font-size: 0.7rem;
  font-weight: 600;
  color: var(--color-accent);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.dialogue-row-title {
  font-family: var(--font-serif);
  font-weight: 700;
  color: var(--color-text);
  text-decoration: none;
}

.dialogue-row-title:hover { color: var(--color-primary); }

.dialogue-status {
  display: inline-block;
  font-size: 0.7rem;
  font-weight: 600;
  padding: 0.15rem 0.5rem;
  border-radius: 999px;
  width: fit-content;
}

.dialogue-status.published {
  background: #dcfce7;
  color: var(--color-success);
}

.dialogue-status.draft {
  background: #fef9c3;
  color: #854d0e;
}

.dialogue-row-meta {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  font-size: 0.8rem;
  color: var(--color-text-muted);
  text-align: right;
  white-space: nowrap;
}
</style>
