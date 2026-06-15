<template>
  <div>
    <header class="sections-header">
      <h1 class="page-title">{{ t('sections.title') }}</h1>
      <button
        type="button"
        class="btn btn-primary"
        :disabled="!auth.isStaff"
        :title="auth.isStaff ? '' : t('sections.adminOnly')"
        @click="showSectionForm = !showSectionForm"
      >
        + {{ t('sections.addSection') }}
      </button>
    </header>

    <form v-if="showSectionForm && auth.isStaff" class="section-form card" @submit.prevent="createSection">
      <div class="form-group">
        <label>{{ t('sections.sectionName') }}</label>
        <input v-model="sectionDraft.name" type="text" required />
      </div>
      <div class="form-group">
        <label>{{ t('sections.sectionSlug') }}</label>
        <input v-model="sectionDraft.slug" type="text" required />
        <p class="field-help">{{ t('sections.sectionSlugHelp') }}</p>
      </div>
      <div class="form-group">
        <label>{{ t('sections.sectionBrief') }}</label>
        <textarea v-model="sectionDraft.brief" rows="3" />
      </div>
      <div class="form-group">
        <label>{{ t('sections.sectionOrder') }}</label>
        <input v-model.number="sectionDraft.order" type="number" min="0" />
        <p class="field-help">{{ t('sections.sectionOrderHelp') }}</p>
      </div>
      <div v-if="sectionFormError" class="alert alert-error">{{ sectionFormError }}</div>
      <div class="form-actions">
        <button class="btn btn-primary" type="submit" :disabled="creatingSection">
          {{ creatingSection ? t('common.loading') : t('common.save') }}
        </button>
        <button class="btn btn-outline" type="button" @click="showSectionForm = false">
          {{ t('common.cancel') }}
        </button>
      </div>
    </form>

    <div v-if="loading" class="text-muted">{{ t('common.loading') }}</div>

    <div v-else class="sections-grid">
      <article
        v-for="(section, index) in sections"
        :key="section.id"
        class="section-card card"
      >
        <RouterLink :to="`/sections/${section.slug}`" class="section-title-button">
          {{ index + 1 }}. {{ section.name }}
        </RouterLink>
        <p v-if="section.brief" class="section-brief">{{ section.brief }}</p>
        <div class="section-footer">
          <span class="dialogue-count">{{ section.dialogue_count }} {{ t('sections.dialogues') }}</span>
        </div>
        <div class="section-actions">
          <button type="button" class="btn btn-outline btn-sm" @click="openResources(section, 'literature')">
            {{ t('dialogues.literature') }}
          </button>
          <button type="button" class="btn btn-outline btn-sm" @click="openResources(section, 'authors')">
            {{ t('dialogue.authors') }}
          </button>
        </div>
      </article>
    </div>

    <SectionResourcesModal
      :open="resourceModalOpen"
      :type="activeResourceType"
      :title="resourceTitle"
      :resources="activeResources"
      :loading="resourcesLoading"
      @close="resourceModalOpen = false"
    />
  </div>
</template>

<script setup>
import { computed, ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import api from '../api'
import { useAuthStore } from '../stores/auth'
import SectionResourcesModal from '../components/SectionResourcesModal.vue'

const { t } = useI18n()
const auth = useAuthStore()
const sections = ref([])
const loading = ref(true)
const showSectionForm = ref(false)
const creatingSection = ref(false)
const sectionFormError = ref('')
const sectionDraft = ref({ name: '', slug: '', brief: '', order: 0 })
const resourceModalOpen = ref(false)
const resourcesLoading = ref(false)
const activeResourceType = ref('literature')
const activeSection = ref(null)
const resourcesBySection = ref({})

const activeResources = computed(() => {
  if (!activeSection.value) return {}
  return resourcesBySection.value[activeSection.value.slug] || {}
})

const resourceTitle = computed(() => {
  if (!activeSection.value) return ''
  const label = activeResourceType.value === 'authors' ? t('dialogue.authors') : t('dialogues.literature')
  return `${label}: ${activeSection.value.name}`
})

onMounted(async () => {
  try {
    if (auth.isAuthenticated && !auth.user) {
      await auth.fetchMe()
    }
    const { data } = await api.get('/sections/')
    sections.value = data.results || data
    sectionDraft.value.order = nextSectionOrder()
  } finally {
    loading.value = false
  }
})

function nextSectionOrder() {
  const maxOrder = sections.value.reduce((max, section) => Math.max(max, section.order || 0), 0)
  return maxOrder + 10
}

async function createSection() {
  if (!auth.isStaff) return
  sectionFormError.value = ''
  creatingSection.value = true
  try {
    const { data } = await api.post('/sections/', sectionDraft.value)
    sections.value.push(data)
    sections.value.sort((a, b) => (a.order - b.order) || a.name.localeCompare(b.name))
    sectionDraft.value = { name: '', slug: '', brief: '', order: nextSectionOrder() }
    showSectionForm.value = false
  } catch (err) {
    sectionFormError.value = err.response?.data?.detail || t('sections.createError')
  } finally {
    creatingSection.value = false
  }
}

async function openResources(section, type) {
  activeSection.value = section
  activeResourceType.value = type
  resourceModalOpen.value = true
  if (resourcesBySection.value[section.slug]) return
  resourcesLoading.value = true
  try {
    const { data } = await api.get(`/sections/${section.slug}/resources/`)
    resourcesBySection.value = { ...resourcesBySection.value, [section.slug]: data }
  } finally {
    resourcesLoading.value = false
  }
}
</script>

<style scoped>
.sections-header {
  align-items: center;
  display: flex;
  gap: 1rem;
  justify-content: space-between;
  margin-bottom: 1.5rem;
}

.sections-header .page-title {
  margin-bottom: 0;
}

.section-form {
  margin-bottom: 1.5rem;
}

.form-actions {
  display: flex;
  gap: 0.75rem;
}

.field-help {
  color: var(--color-text-muted);
  font-size: 0.78rem;
  line-height: 1.4;
  margin: 0;
}

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

.section-title-button {
  align-self: flex-start;
  border: 1px solid var(--color-primary);
  border-radius: var(--radius);
  color: var(--color-primary);
  font-family: var(--font-serif);
  font-size: 1rem;
  font-weight: 700;
  line-height: 1.4;
  padding: 0.45rem 0.65rem;
  text-decoration: none;
}

.section-title-button:hover {
  background: var(--color-primary);
  color: white;
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

.section-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin-top: 0.25rem;
}

.btn-sm {
  font-size: 0.82rem;
  padding: 0.375rem 0.75rem;
}
</style>
