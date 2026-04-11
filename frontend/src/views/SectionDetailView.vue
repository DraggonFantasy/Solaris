<template>
  <div v-if="section">
    <RouterLink to="/sections" class="back-link">← {{ t('common.back') }}</RouterLink>
    <h1 class="page-title">{{ section.name }}</h1>
    <p v-if="section.brief" class="section-brief">{{ section.brief }}</p>

    <div v-if="loading" class="text-muted">{{ t('common.loading') }}</div>
    <div v-else-if="dialogues.length === 0" class="text-muted">{{ t('dialogues.noDialogues') }}</div>
    <div v-else class="dialogue-list">
      <RouterLink
        v-for="d in dialogues"
        :key="d.id"
        :to="`/dialogues/${d.id}`"
        class="dialogue-row card"
      >
        <div class="dialogue-row-main">
          <h3 class="dialogue-row-title">{{ d.title }}</h3>
          <p v-if="d.summary" class="dialogue-row-summary">{{ d.summary }}</p>
        </div>
        <div class="dialogue-row-meta">
          <span v-if="d.human_author_username">{{ t('dialogues.by') }}: {{ d.human_author_username }}</span>
          <span v-if="d.llm_name">{{ t('dialogues.model') }}: {{ d.llm_name }}</span>
          <span>♥ {{ d.likes_count }}</span>
        </div>
      </RouterLink>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import api from '../api'

const { t } = useI18n()
const route = useRoute()
const section = ref(null)
const dialogues = ref([])
const loading = ref(true)

onMounted(async () => {
  try {
    const [sectionRes, dialogueRes] = await Promise.all([
      api.get(`/sections/${route.params.slug}/`),
      api.get(`/dialogues/?section=${route.params.slug}`)
    ])
    section.value = sectionRes.data
    dialogues.value = dialogueRes.data.results || dialogueRes.data
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.back-link {
  color: var(--color-text-muted);
  text-decoration: none;
  font-size: 0.875rem;
  display: inline-block;
  margin-bottom: 1rem;
}

.back-link:hover { color: var(--color-primary); }

.section-brief {
  color: var(--color-text-muted);
  margin-bottom: 2rem;
  line-height: 1.7;
  max-width: 760px;
}

.dialogue-list {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.dialogue-row {
  text-decoration: none;
  color: inherit;
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 1rem;
  transition: box-shadow 0.2s;
}

.dialogue-row:hover { box-shadow: var(--shadow-md); }

.dialogue-row-main { flex: 1; }

.dialogue-row-title {
  font-family: var(--font-serif);
  font-size: 1rem;
  margin-bottom: 0.375rem;
}

.dialogue-row-summary {
  font-size: 0.875rem;
  color: var(--color-text-muted);
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
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
