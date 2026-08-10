<template>
  <div v-if="section">
    <RouterLink to="/sections" class="back-link">← {{ t('common.back') }}</RouterLink>
    <div class="section-header">
      <div>
        <h1 class="page-title">{{ sectionNumber }}. {{ section.name }}</h1>
        <p v-if="section.brief" class="section-brief">{{ section.brief }}</p>
      </div>
      <div class="section-actions">
        <RouterLink
          class="btn btn-primary section-action-btn"
          :to="{ name: 'create-dialogue', query: { section: section.slug } }"
        >
          + {{ t('dialogue.createInSection') }}
        </RouterLink>
        <button type="button" class="btn btn-outline section-action-btn" @click="openResources('literature')">
          {{ t('dialogues.literatureShort') }}
        </button>
        <button type="button" class="btn btn-outline section-action-btn" @click="openResources('authors')">
          {{ t('dialogue.authors') }}
        </button>
        <button type="button" class="btn btn-outline section-action-btn" @click="openResources('illustrations')">
          {{ t('dialogues.illustrations') }}
        </button>
      </div>
    </div>

    <div v-if="loading" class="text-muted">{{ t('common.loading') }}</div>
    <div v-else-if="dialogues.length === 0" class="text-muted">{{ t('dialogues.noDialogues') }}</div>
    <div v-else class="dialogue-list">
      <article
        v-for="(d, index) in dialogues"
        :key="d.id"
        class="dialogue-row card"
      >
        <div class="dialogue-row-main">
          <RouterLink :to="`/dialogues/${d.id}`" class="dialogue-title-button">
            {{ index + 1 }}. {{ d.title }}
          </RouterLink>
          <p v-if="d.summary" class="dialogue-row-summary">{{ d.summary }}</p>
        </div>
        <div class="dialogue-row-actions">
          <RouterLink
            v-if="auth.isStaff"
            class="btn btn-primary btn-sm"
            :to="{ name: 'edit-dialogue', params: { id: d.id } }"
          >
            {{ t('dialogue.edit') }}
          </RouterLink>
          <button type="button" class="btn btn-outline btn-sm" @click="openDialogueInfo(d, 'authors')">
            {{ t('dialogues.by') }}
          </button>
          <button type="button" class="btn btn-outline btn-sm" @click="openDialogueInfo(d, 'literature')">
            {{ t('dialogues.literatureShort') }}
          </button>
          <button type="button" class="btn btn-outline btn-sm" @click="openDialogueInfo(d, 'comments')">
            {{ t('dialogues.comments') }}
          </button>
          <button type="button" class="btn btn-outline btn-sm" @click="openDialogueInfo(d, 'illustrations')">
            {{ t('dialogues.illustrations') }}
          </button>
          <button type="button" class="btn btn-outline btn-sm" @click="openDialogueInfo(d, 'ai_model')">
            {{ t('dialogues.aiModel') }}
          </button>
        </div>
      </article>
    </div>

    <SectionResourcesModal
      :open="resourceModalOpen"
      :type="activeResourceType"
      :title="resourceTitle"
      :resources="sectionResources"
      :loading="resourcesLoading"
      @close="resourceModalOpen = false"
    />

    <DialogueResourcesModal
      :open="dialogueModal.open"
      :type="dialogueModal.type"
      :dialogue="dialogueModal.dialogue"
      @close="closeDialogueInfo"
      @updated="updateDialogueInList"
    />
  </div>
</template>

<script setup>
import { computed, ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import api from '../api'
import { useAuthStore } from '../stores/auth'
import DialogueResourcesModal from '../components/DialogueResourcesModal.vue'
import SectionResourcesModal from '../components/SectionResourcesModal.vue'

const { t } = useI18n()
const route = useRoute()
const auth = useAuthStore()
const section = ref(null)
const dialogues = ref([])
const sections = ref([])
const loading = ref(true)
const resourceModalOpen = ref(false)
const resourcesLoading = ref(false)
const activeResourceType = ref('literature')
const sectionResources = ref({})
const dialogueModal = ref({ open: false, type: 'authors', dialogue: null })

const sectionNumber = computed(() => {
  if (!section.value) return 1
  const index = sections.value.findIndex((item) => item.slug === section.value.slug)
  return index >= 0 ? index + 1 : Math.max(1, Math.round((section.value.order || 10) / 10))
})

const resourceTitle = computed(() => {
  if (!section.value) return ''
  const labels = {
    literature: t('dialogues.literature'),
    authors: t('dialogue.authors'),
    illustrations: t('dialogues.illustrations'),
  }
  return `${labels[activeResourceType.value]}: ${section.value.name}`
})

onMounted(async () => {
  try {
    if (auth.isAuthenticated && !auth.user) {
      await auth.fetchMe()
    }
    const [sectionRes, dialogueRes, sectionsRes] = await Promise.all([
      api.get(`/sections/${route.params.slug}/`),
      api.get(`/dialogues/?section=${route.params.slug}`),
      api.get('/sections/'),
    ])
    section.value = sectionRes.data
    dialogues.value = dialogueRes.data.results || dialogueRes.data
    sections.value = sectionsRes.data.results || sectionsRes.data
  } finally {
    loading.value = false
  }
})

async function openResources(type) {
  activeResourceType.value = type
  resourceModalOpen.value = true
  if (sectionResources.value.section) return
  resourcesLoading.value = true
  try {
    const { data } = await api.get(`/sections/${route.params.slug}/resources/`)
    sectionResources.value = data
  } finally {
    resourcesLoading.value = false
  }
}

function openDialogueInfo(dialogue, type) {
  dialogueModal.value = { open: true, type, dialogue }
}

function closeDialogueInfo() {
  dialogueModal.value = { open: false, type: 'authors', dialogue: null }
}

function updateDialogueInList(updatedDialogue) {
  const index = dialogues.value.findIndex((dialogue) => dialogue.id === updatedDialogue.id)
  if (index >= 0) {
    dialogues.value[index] = { ...dialogues.value[index], ...updatedDialogue }
  }
  if (dialogueModal.value.dialogue?.id === updatedDialogue.id) {
    dialogueModal.value.dialogue = { ...dialogueModal.value.dialogue, ...updatedDialogue }
  }
}
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

.section-header {
  align-items: flex-start;
  display: flex;
  gap: 1.5rem;
  justify-content: space-between;
  margin-bottom: 2rem;
}

.section-header .page-title {
  margin-bottom: 0.75rem;
}

.section-brief {
  color: var(--color-text-muted);
  line-height: 1.7;
  max-width: 760px;
}

.section-actions {
  display: flex;
  flex-shrink: 0;
  flex-wrap: nowrap;
  gap: 0.35rem;
  justify-content: flex-end;
}

.section-action-btn {
  font-size: 0.82rem;
  padding: 0.4rem 0.7rem;
  white-space: nowrap;
}

.dialogue-list {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.dialogue-row {
  color: inherit;
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 1rem;
  transition: box-shadow 0.2s;
}

.dialogue-row:hover { box-shadow: var(--shadow-md); }

.dialogue-row-main {
  flex: 1;
  min-width: 0;
}

.dialogue-title-button {
  color: var(--color-primary);
  display: inline-flex;
  font-family: var(--font-serif);
  font-size: 1rem;
  font-weight: 700;
  line-height: 1.4;
  margin-bottom: 0.375rem;
  text-decoration: none;
}

.dialogue-title-button:hover {
  text-decoration: underline;
}

.dialogue-row-summary {
  font-size: 0.875rem;
  color: var(--color-text-muted);
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.dialogue-row-actions {
  display: flex;
  flex-shrink: 0;
  flex-wrap: nowrap;
  gap: 0.35rem;
  justify-content: flex-end;
}

.btn-sm {
  font-size: 0.76rem;
  padding: 0.32rem 0.52rem;
  white-space: nowrap;
}

@media (max-width: 640px) {
  .section-header {
    flex-direction: column;
  }

  .section-actions,
  .dialogue-row-actions {
    flex-wrap: wrap;
    justify-content: flex-start;
  }

  .dialogue-row {
    flex-direction: column;
  }
}
</style>
