<template>
  <div>
    <h1 class="page-title">{{ t('sections.title') }}</h1>

    <div v-if="loading" class="text-muted">{{ t('common.loading') }}</div>

    <div v-else class="sections-grid">
      <article
        v-for="section in sections"
        :key="section.id"
        class="section-card card"
      >
        <RouterLink :to="`/sections/${section.slug}`" class="section-main-link">
          <h2 class="section-name">{{ section.name }}</h2>
        </RouterLink>
        <p v-if="section.brief" class="section-brief">{{ section.brief }}</p>
        <div class="section-footer">
          <span class="dialogue-count">{{ section.dialogue_count }} {{ t('sections.dialogues') }}</span>
          <RouterLink :to="`/sections/${section.slug}`" class="view-link">{{ t('sections.viewSection') }} →</RouterLink>
        </div>
        <RouterLink
          class="btn btn-outline btn-sm add-dialogue-link"
          :to="{ name: 'create-dialogue', query: { section: section.slug } }"
        >
          + {{ t('dialogue.createInSection') }}
        </RouterLink>
      </article>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import api from '../api'

const { t } = useI18n()
const sections = ref([])
const loading = ref(true)

onMounted(async () => {
  try {
    const { data } = await api.get('/sections/')
    sections.value = data.results || data
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.sections-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 1.25rem;
}

.section-card {
  color: inherit;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  transition: box-shadow 0.2s, transform 0.2s;
}

.section-card:hover {
  box-shadow: var(--shadow-md);
  transform: translateY(-2px);
}

.section-main-link {
  color: inherit;
  text-decoration: none;
}

.section-name {
  font-family: var(--font-serif);
  font-size: 1.125rem;
  color: var(--color-primary);
}

.section-brief {
  font-size: 0.9rem;
  color: var(--color-text-muted);
  flex: 1;
  line-height: 1.6;
}

.section-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 0.5rem;
  font-size: 0.8125rem;
}

.dialogue-count {
  color: var(--color-text-muted);
}

.view-link {
  color: var(--color-primary);
  font-weight: 500;
  text-decoration: none;
}

.view-link:hover {
  text-decoration: underline;
}

.add-dialogue-link {
  align-self: flex-start;
  margin-top: 0.25rem;
}
</style>
