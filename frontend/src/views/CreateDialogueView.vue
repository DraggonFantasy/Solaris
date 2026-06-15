<template>
  <div class="create-page">
    <h1 class="page-title">{{ t('dialogue.createTitle') }}</h1>

    <!-- Step indicator -->
    <div class="steps">
      <div
        v-for="(step, i) in steps"
        :key="i"
        class="step"
        :class="{ active: currentStep === i, done: currentStep > i }"
      >
        <div class="step-circle">{{ currentStep > i ? '✓' : i + 1 }}</div>
        <span class="step-label">{{ step }}</span>
      </div>
      <div class="step-line" />
    </div>

    <div class="wizard-body card">

      <!-- Step 0: Context -->
      <div v-if="currentStep === 0">
        <h2 class="step-title">{{ t('dialogue.step1Title') }}</h2>

        <div class="form-group">
          <label>{{ t('dialogue.section') }} *</label>
          <select v-model="form.section" required>
            <option value="" disabled>— {{ t('dialogue.selectSection') }} —</option>
            <option v-for="s in sections" :key="s.id" :value="s.id">{{ s.name }}</option>
          </select>
        </div>

        <div class="form-group">
          <label>{{ t('dialogue.title') }} *</label>
          <input v-model="form.title" type="text" :placeholder="t('dialogue.titlePlaceholder')" required />
        </div>

        <div class="form-group">
          <label>{{ t('dialogue.description') }} *</label>
          <textarea v-model="form.summary" rows="3" :placeholder="t('dialogue.descriptionPlaceholder')" />
        </div>

        <div class="form-group">
          <label>{{ t('dialogue.authors') }}</label>
          <div class="author-list">
            <div v-for="(author, index) in authors" :key="author.localId" class="author-chip">
              <div>
                <strong>{{ author.name }}</strong>
                <span>{{ authorKindLabel(author.kind) }}</span>
                <small v-if="author.version">{{ author.version }}</small>
              </div>
              <div v-if="canModifyAuthor(author)" class="chip-actions">
                <button
                  type="button"
                  class="chip-edit"
                  @click="openAuthorModal(index)"
                >
                  {{ t('dialogue.editAuthor') }}
                </button>
                <button
                  type="button"
                  class="chip-remove"
                  :aria-label="t('dialogue.removeAuthor')"
                  @click="removeAuthor(index)"
                >
                  ×
                </button>
              </div>
            </div>
            <button type="button" class="add-author-card" @click="openAuthorModal()">
              + {{ t('dialogue.addAuthor') }}
            </button>
          </div>
          <datalist id="author-suggestions">
            <option v-for="author in authorSuggestions" :key="author.name" :value="author.name" />
          </datalist>
        </div>

        <div class="form-group">
          <label>{{ t('dialogue.style') }}</label>
          <select v-model="form.style">
            <option value="other">{{ t('dialogue.styleOther') }}</option>
            <option value="socratic">{{ t('dialogue.styleSocratic') }}</option>
            <option value="dialectical">{{ t('dialogue.styleDialectical') }}</option>
            <option value="rhetorical">{{ t('dialogue.styleRhetorical') }}</option>
            <option value="debate">{{ t('dialogue.styleDebate') }}</option>
          </select>
        </div>
      </div>

      <!-- Step 1: Dialogue text -->
      <div v-if="currentStep === 1">
        <div class="dialogue-text-header">
          <div>
            <h2 class="step-title">{{ t('dialogue.step2Title') }}</h2>
            <p class="step-hint">{{ t('dialogue.step2Hint') }}</p>
          </div>
          <div class="import-menu-wrap">
            <button type="button" class="btn btn-outline" @click="showImportMenu = !showImportMenu">
              {{ importingShare ? t('common.loading') : t('dialogue.importFrom') }}
            </button>
            <div v-if="showImportMenu" class="import-menu">
              <button
                v-for="source in importSources"
                :key="source.name"
                type="button"
                @click="handleImport(source.name)"
              >
                <span class="source-icon">{{ source.short }}</span>
                {{ source.name }}
              </button>
            </div>
          </div>
        </div>
        <div class="dialogue-editor-layout">
          <MarkdownEditor
            v-model="form.text"
            :placeholder="dialoguePlaceholder"
            :image-button-title="t('dialogue.inlineImageButton')"
            :drop-image-hint="t('dialogue.inlineImageDropHint')"
            @add-inline-image="queueInlineImage"
          />
          <aside class="speakers-panel" v-if="false">
            <div class="speakers-panel-header">
              <h3>{{ t('dialogue.speakersTitle') }}</h3>
              <span>{{ dialogueSpeakers.length }}</span>
            </div>
            <div v-if="dialogueSpeakers.length" class="speaker-list">
              <button
                v-for="speaker in dialogueSpeakers"
                :key="speaker"
                type="button"
                class="speaker-item"
                @click="insertSpeakerTurn(speaker)"
              >
                {{ speaker }}
              </button>
            </div>
            <p v-else class="empty-speakers">{{ t('dialogue.noSpeakers') }}</p>

            <form class="speaker-add-form" @submit.prevent="addSpeaker">
              <input
                v-model="speakerDraft"
                type="text"
                :placeholder="t('dialogue.speakerNamePlaceholder')"
              />
              <button type="submit" class="btn btn-primary btn-sm" :disabled="!speakerDraft.trim()">
                + {{ t('dialogue.addSpeaker') }}
              </button>
            </form>
          </aside>
        </div>
        <div v-if="textStepError" class="alert alert-error dialogue-step-error">{{ textStepError }}</div>
      </div>

      <!-- Step 2: Extras -->
      <div v-if="currentStep === 2">
        <h2 class="step-title">{{ t('dialogue.step3Title') }}</h2>

        <div class="form-group">
          <label>{{ t('dialogues.foodForThought') }}</label>
          <textarea v-model="form.food_for_thought" rows="3" :placeholder="t('dialogue.foodPlaceholder')" />
        </div>

        <div class="form-group">
          <label>{{ t('dialogues.literature') }}</label>
          <textarea v-model="form.recommended_literature" rows="3" :placeholder="t('dialogue.literaturePlaceholder')" />
        </div>

        <div class="form-group">
          <label>{{ t('dialogue.reviewNote') }}</label>
          <textarea v-model="form.review_note" rows="3" :placeholder="t('dialogue.reviewNotePlaceholder')" />
        </div>

        <div class="form-group">
          <label>{{ t('dialogue.illustrationsMenu') }}</label>
          <div class="illustration-editor">
            <div v-if="existingIllustrations.length" class="illustration-list">
              <div v-for="illustration in existingIllustrations" :key="illustration.id" class="illustration-edit-row">
                <img :src="illustration.image" :alt="illustration.caption" />
                <textarea
                  v-model="illustration.caption"
                  rows="3"
                  :placeholder="t('dialogue.illustrationCaptionPlaceholder')"
                />
                <button type="button" class="btn btn-outline btn-sm" @click="removeExistingIllustration(illustration.id)">
                  {{ t('dialogue.removeIllustration') }}
                </button>
              </div>
            </div>

            <div v-if="newIllustrations.length" class="illustration-list">
              <div v-for="(illustration, index) in newIllustrations" :key="illustration.localId" class="illustration-edit-row">
                <div class="illustration-file-name">{{ illustration.file.name }}</div>
                <textarea
                  v-model="illustration.caption"
                  rows="3"
                  :placeholder="t('dialogue.illustrationCaptionPlaceholder')"
                />
                <button type="button" class="btn btn-outline btn-sm" @click="removeNewIllustration(index)">
                  {{ t('dialogue.removeIllustration') }}
                </button>
              </div>
            </div>

            <label class="illustration-upload">
              <input type="file" accept="image/*" multiple @change="addIllustrationFiles" />
              <span class="btn btn-outline btn-sm">+ {{ t('dialogue.addIllustration') }}</span>
            </label>
          </div>
        </div>

        <div v-if="error" class="alert alert-error">{{ error }}</div>
      </div>

    </div>

    <div v-if="showAuthorModal" class="modal-backdrop" @click.self="closeAuthorModal">
      <form class="modal-panel" @submit.prevent="saveAuthor">
        <header class="modal-header">
          <h2>{{ editingAuthorIndex === null ? t('dialogue.addAuthor') : t('dialogue.editAuthor') }}</h2>
          <button type="button" class="modal-close" :aria-label="t('common.cancel')" @click="closeAuthorModal">×</button>
        </header>

        <div class="form-group">
          <label>{{ t('dialogue.authorType') }}</label>
          <select v-model="authorDraft.kind">
            <option value="person">{{ t('dialogue.authorKindPerson') }}</option>
            <option value="ai_model">{{ t('dialogue.authorKindAi') }}</option>
            <option value="organization">{{ t('dialogue.authorKindOrganization') }}</option>
          </select>
        </div>

        <div class="form-group">
          <label>{{ t('dialogue.authorName') }}</label>
          <input
            v-model="authorDraft.name"
            type="text"
            list="author-suggestions"
            :placeholder="t('dialogue.authorNamePlaceholder')"
            autofocus
          />
        </div>

        <div class="form-group">
          <label>{{ t('dialogue.authorVersion') }}</label>
          <input
            v-model="authorDraft.version"
            type="text"
            :placeholder="t('dialogue.authorVersionPlaceholder')"
          />
        </div>

        <div class="form-group">
          <label>{{ t('dialogue.authorDescription') }}</label>
          <textarea
            v-model="authorDraft.description"
            rows="3"
            :placeholder="t('dialogue.authorDescriptionPlaceholder')"
          />
        </div>

        <footer class="modal-actions">
          <button type="button" class="btn btn-outline" @click="closeAuthorModal">{{ t('common.cancel') }}</button>
          <button type="submit" class="btn btn-primary" :disabled="!authorDraft.name.trim()">
            {{ editingAuthorIndex === null ? t('dialogue.addAuthor') : t('common.save') }}
          </button>
        </footer>
      </form>
    </div>

    <!-- Navigation -->
    <div class="wizard-nav">
      <button v-if="currentStep > 0" class="btn btn-outline" @click="currentStep--">
        ← {{ t('common.back') }}
      </button>
      <div class="nav-right">
        <button
          v-if="currentStep < steps.length - 1"
          class="btn btn-primary"
          :disabled="!canProceed"
          @click="nextStep"
        >
          {{ t('dialogue.next') }} →
        </button>
        <template v-else>
          <button class="btn btn-outline" :disabled="submitting" @click="submit(false)">
            {{ isEditing ? t('dialogue.saveChanges') : t('dialogue.saveDraft') }}
          </button>
          <button class="btn btn-primary" :disabled="submitting" @click="submit(true)">
            {{ submitting ? t('common.loading') : t('dialogue.submitReview') }}
          </button>
        </template>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useAuthStore } from '../stores/auth'
import api from '../api'
import MarkdownEditor from '../components/MarkdownEditor.vue'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

const currentStep = ref(0)
const submitting = ref(false)
const error = ref('')
const textStepError = ref('')
const showAuthorModal = ref(false)
const editingAuthorIndex = ref(null)
const showImportMenu = ref(false)
const importingShare = ref(false)
const sections = ref([])
const authors = ref([])
const existingIllustrations = ref([])
const removedIllustrationIds = ref([])
const newIllustrations = ref([])
const pendingInlineImages = ref([])
const speakerDraft = ref('')
const originalStatus = ref('draft')

const importSources = [
  { name: 'ChatGPT', short: 'CG' },
  { name: 'Claude', short: 'CL' },
  { name: 'Gemini', short: 'GM' },
]

const authorSuggestions = [
  { kind: 'ai_model', name: 'ChatGPT GPT-4.1' },
  { kind: 'ai_model', name: 'Claude 3.5 Sonnet' },
  { kind: 'ai_model', name: 'Gemini 1.5 Pro' },
  { kind: 'ai_model', name: 'GPT-4' },
]

const authorDraft = ref({
  kind: 'ai_model',
  name: '',
  version: '',
  description: '',
})

const steps = computed(() => [
  t('dialogue.step1'),
  t('dialogue.step2'),
  t('dialogue.step3'),
])

const isEditing = computed(() => route.name === 'edit-dialogue')

const form = ref({
  section: '',
  title: '',
  llm_name: '',
  llm_version: '',
  style: 'other',
  text: '',
  summary: '',
  food_for_thought: '',
  recommended_literature: '',
  review_note: '',
})

const dialoguePlaceholder = computed(() => {
  return `## Сократ

Напишіть репліку першого співрозмовника...


## LLM-агент

Напишіть відповідь...
`
})

const dialogueSpeakers = computed(() => {
  const names = []
  const seen = new Set()
  const matches = form.value.text.matchAll(/^##\s+(.+?)\s*$/gm)
  for (const match of matches) {
    const name = match[1].trim()
    if (name && !seen.has(name)) {
      seen.add(name)
      names.push(name)
    }
  }
  return names
})

const canProceed = computed(() => {
  if (currentStep.value === 0) {
    return form.value.section && form.value.title.trim() && form.value.summary.trim() && authors.value.length > 0
  }
  return true
})

onMounted(async () => {
  if (auth.isAuthenticated && !auth.user) {
    await auth.fetchMe()
  }
  const sectionRes = await api.get('/sections/')
  sections.value = sectionRes.data.results || sectionRes.data
  if (isEditing.value) {
    await loadDialogue()
  } else {
    applySectionFromQuery()
    initDefaultAuthor()
    restoreAuthorPresets()
  }
})

function applySectionFromQuery() {
  const sectionParam = route.query.section
  if (!sectionParam) return
  const selected = sections.value.find((section) => {
    return String(section.id) === String(sectionParam) || section.slug === sectionParam
  })
  if (selected) {
    form.value.section = selected.id
  }
}

function nextStep() {
  if (currentStep.value === 1 && !validateTextStep()) return
  textStepError.value = ''
  if (canProceed.value) currentStep.value++
}

function validateTextStep() {
  if (!form.value.text.trim()) {
    textStepError.value = t('dialogue.textRequired')
    return false
  }
  /*
  if (!dialogueSpeakers.value.length) {
    textStepError.value = t('dialogue.speakerHeadingRequired')
    return false
  }
  */
  return true
}

async function submit(submitForReview) {
  error.value = ''
  submitting.value = true
  try {
    persistAuthorPresets()
    const firstAiAuthor = authors.value.find((author) => author.kind === 'ai_model')
    const payload = {
      ...form.value,
      authors: authors.value.map(({ localId, ...author }) => author),
      llm_name: firstAiAuthor?.name || '',
      llm_version: firstAiAuthor?.version || '',
      status: isEditing.value ? originalStatus.value : 'draft',
      published: false
    }
    let { data } = isEditing.value
      ? await api.put(`/dialogues/${route.params.id}/`, payload)
      : await api.post('/dialogues/', payload)
    const inlineImagesChanged = await syncInlineImages(data.id)
    if (inlineImagesChanged) {
      payload.text = form.value.text
      const response = await api.put(`/dialogues/${data.id}/`, payload)
      data = response.data
    }
    await syncIllustrations(data.id)
    if (submitForReview) {
      const submitPayload = { ...payload, status: 'submitted' }
      const response = await api.put(`/dialogues/${data.id}/`, submitPayload)
      data = response.data
    }
    if (submitForReview && data.status === 'published') {
      router.push({ name: 'dialogue-detail', params: { id: data.id } })
    } else if (submitForReview) {
      router.push({ name: 'dialogue-submitted', params: { id: data.id } })
    } else {
      router.push({ name: 'my-dialogues' })
    }
  } catch (err) {
    error.value = err.response?.data
      ? JSON.stringify(err.response.data)
      : t('common.error')
  } finally {
    submitting.value = false
  }
}

async function loadDialogue() {
  const { data } = await api.get(`/dialogues/${route.params.id}/`)
  originalStatus.value = data.status || 'draft'
  form.value = {
    section: data.section,
    title: data.title || '',
    llm_name: data.llm_name || '',
    llm_version: data.llm_version || '',
    style: data.style || 'other',
    text: data.text || '',
    summary: data.summary || '',
    food_for_thought: data.food_for_thought || '',
    recommended_literature: data.recommended_literature || '',
    review_note: data.review_note || '',
  }
  authors.value = (data.authors || []).map((author) => ({
    ...author,
    localId: crypto.randomUUID?.() || `${Date.now()}-${Math.random()}`,
  }))
  existingIllustrations.value = (data.illustrations || []).map((illustration) => ({
    ...illustration,
    originalCaption: illustration.caption || '',
    originalOrder: illustration.order || 0,
  }))
  removedIllustrationIds.value = []
  newIllustrations.value = []
  if (!authors.value.length) {
    initDefaultAuthor()
  }
}

function initDefaultAuthor() {
  if (!auth.user || authors.value.some((author) => author.is_current_user)) return
  const displayName = [auth.user.first_name, auth.user.last_name].filter(Boolean).join(' ') || auth.user.username
  authors.value.unshift({
    localId: `current-user-${auth.user.id}`,
    kind: 'person',
    name: displayName,
    version: '',
    description: auth.user.bio || '',
    is_current_user: true,
  })
}

function restoreAuthorPresets() {
  try {
    const saved = JSON.parse(localStorage.getItem('solaris_author_presets') || '[]')
    saved.forEach((author) => {
      if (!authors.value.some((item) => item.name === author.name && item.kind === author.kind)) {
        authors.value.push({ ...author, localId: crypto.randomUUID?.() || `${Date.now()}-${Math.random()}` })
      }
    })
  } catch {
    // Ignore malformed local storage.
  }
}

function persistAuthorPresets() {
  const reusable = authors.value
    .filter((author) => !author.is_current_user)
    .map(({ localId, ...author }) => author)
  localStorage.setItem('solaris_author_presets', JSON.stringify(reusable.slice(0, 20)))
}

function saveAuthor() {
  const name = authorDraft.value.name.trim()
  if (!name) return
  const author = {
    kind: authorDraft.value.kind,
    name,
    version: authorDraft.value.version.trim(),
    description: authorDraft.value.description.trim(),
  }
  const currentIndex = editingAuthorIndex.value
  const duplicate = authors.value.some((item, index) => {
    return index !== currentIndex && item.name === author.name && item.kind === author.kind
  })
  if (duplicate) {
    closeAuthorModal()
    return
  }
  if (currentIndex === null) {
    authors.value.push({
      ...author,
      localId: crypto.randomUUID?.() || `${Date.now()}-${Math.random()}`,
      is_current_user: false,
    })
  } else {
    const existing = authors.value[currentIndex]
    authors.value[currentIndex] = {
      ...existing,
      ...author,
    }
  }
  closeAuthorModal()
}

function removeAuthor(index) {
  authors.value.splice(index, 1)
}

function canModifyAuthor(author) {
  return auth.isStaff || !author.is_current_user
}

function openAuthorModal(index = null) {
  editingAuthorIndex.value = index
  if (index !== null) {
    const author = authors.value[index]
    authorDraft.value = {
      kind: author.kind || 'person',
      name: author.name || '',
      version: author.version || '',
      description: author.description || '',
    }
  }
  showAuthorModal.value = true
}

function closeAuthorModal() {
  showAuthorModal.value = false
  editingAuthorIndex.value = null
  authorDraft.value = { kind: 'ai_model', name: '', version: '', description: '' }
}

function authorKindLabel(kind) {
  if (kind === 'ai_model') return t('dialogue.authorKindAi')
  if (kind === 'organization') return t('dialogue.authorKindOrganization')
  return t('dialogue.authorKindPerson')
}

function addSpeaker() {
  const name = speakerDraft.value.trim()
  if (!name) return
  insertSpeakerTurn(name)
  speakerDraft.value = ''
}

function insertSpeakerTurn(speaker) {
  const val = form.value.text
  const suffix = val && !val.endsWith('\n\n') ? (val.endsWith('\n') ? '\n' : '\n\n') : ''
  form.value.text = `${val}${suffix}## ${speaker}\n\n`
}

function queueInlineImage(payload) {
  pendingInlineImages.value.push(payload)
}

async function syncInlineImages(dialogueId) {
  if (!pendingInlineImages.value.length) return false
  const queue = [...pendingInlineImages.value]
  pendingInlineImages.value = []
  let textChanged = false

  for (let index = 0; index < queue.length; index += 1) {
    const item = queue[index]
    if (!form.value.text.includes(item.placeholder)) {
      URL.revokeObjectURL(item.placeholder)
      continue
    }
    try {
      const data = new FormData()
      data.append('image', item.file)
      const response = await api.post(`/dialogues/${dialogueId}/inline-images/`, data)
      form.value.text = form.value.text.split(item.placeholder).join(response.data.image)
      URL.revokeObjectURL(item.placeholder)
      textChanged = true
    } catch (err) {
      pendingInlineImages.value.push(item, ...queue.slice(index + 1))
      throw err
    }
  }

  return textChanged
}

function addIllustrationFiles(event) {
  Array.from(event.target.files || []).forEach((file) => {
    newIllustrations.value.push({
      localId: crypto.randomUUID?.() || `${Date.now()}-${Math.random()}`,
      file,
      caption: '',
    })
  })
  event.target.value = ''
}

function removeNewIllustration(index) {
  newIllustrations.value.splice(index, 1)
}

function removeExistingIllustration(id) {
  existingIllustrations.value = existingIllustrations.value.filter((illustration) => illustration.id !== id)
  if (!removedIllustrationIds.value.includes(id)) {
    removedIllustrationIds.value.push(id)
  }
}

async function syncIllustrations(dialogueId) {
  await Promise.all(removedIllustrationIds.value.map((id) => api.delete(`/illustrations/${id}/`)))
  await Promise.all(existingIllustrations.value.map((illustration, index) => {
    if (
      illustration.caption === illustration.originalCaption
      && index === illustration.originalOrder
    ) {
      return Promise.resolve()
    }
    const data = new FormData()
    data.append('caption', illustration.caption || '')
    data.append('order', index)
    return api.patch(`/illustrations/${illustration.id}/`, data)
  }))
  await Promise.all(newIllustrations.value.map((illustration, index) => {
    const data = new FormData()
    data.append('image', illustration.file)
    data.append('caption', illustration.caption || '')
    data.append('order', existingIllustrations.value.length + index)
    return api.post(`/dialogues/${dialogueId}/illustrations/`, data)
  }))
}

async function handleImport(source) {
  showImportMenu.value = false
  const url = window.prompt(t('dialogue.importUrlPrompt', { source }))
  if (!url) return
  textStepError.value = ''
  importingShare.value = true
  try {
    const { data } = await api.post('/dialogues/import-share/', { url })
    const suffix = form.value.text && !form.value.text.endsWith('\n\n')
      ? (form.value.text.endsWith('\n') ? '\n' : '\n\n')
      : ''
    form.value.text = `${form.value.text}${suffix}${data.markdown}`
    if (!form.value.title.trim() && data.title) {
      form.value.title = data.title
    }
    const serviceAuthor = importSources.find((item) => item.name.toLowerCase() === data.service)
    if (serviceAuthor && !authors.value.some((author) => author.kind === 'ai_model' && author.name === serviceAuthor.name)) {
      authors.value.push({
        localId: crypto.randomUUID?.() || `${Date.now()}-${Math.random()}`,
        kind: 'ai_model',
        name: serviceAuthor.name,
        version: '',
        description: '',
      })
    }
  } catch (err) {
    textStepError.value = err.response?.data?.detail || t('dialogue.importError')
  } finally {
    importingShare.value = false
  }
}
</script>

<style scoped>
.steps {
  display: flex;
  align-items: center;
  margin-bottom: 2rem;
  position: relative;
}

.step-line {
  position: absolute;
  top: 18px;
  left: 0;
  right: 0;
  height: 2px;
  background: var(--color-border);
  z-index: 0;
}

.step {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.4rem;
  flex: 1;
  z-index: 1;
}

.step-circle {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  border: 2px solid var(--color-border);
  background: var(--color-surface);
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 600;
  font-size: 0.875rem;
  color: var(--color-text-muted);
  transition: all 0.2s;
}

.step.active .step-circle {
  border-color: var(--color-primary);
  background: var(--color-primary);
  color: white;
}

.step.done .step-circle {
  border-color: var(--color-success);
  background: var(--color-success);
  color: white;
}

.step-label {
  font-size: 0.75rem;
  color: var(--color-text-muted);
  font-weight: 500;
}

.step.active .step-label {
  color: var(--color-primary);
}

.wizard-body {
  min-height: 400px;
  margin-bottom: 1.5rem;
}

.step-title {
  font-family: var(--font-serif);
  font-size: 1.125rem;
  color: var(--color-primary);
  margin-bottom: 1.5rem;
}

.step-hint {
  font-size: 0.875rem;
  color: var(--color-text-muted);
  margin-bottom: 1rem;
}

.dialogue-text-header {
  align-items: flex-start;
  display: flex;
  gap: 1rem;
  justify-content: space-between;
  margin-bottom: 1rem;
}

.dialogue-text-header .step-title {
  margin-bottom: 0.5rem;
}

.dialogue-text-header .step-hint {
  margin-bottom: 0;
}

.import-menu-wrap {
  position: relative;
}

.import-menu {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  box-shadow: var(--shadow-md);
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  min-width: 180px;
  padding: 0.35rem;
  position: absolute;
  right: 0;
  top: calc(100% + 0.35rem);
  z-index: 20;
}

.import-menu button {
  align-items: center;
  background: transparent;
  border: 0;
  border-radius: 4px;
  color: var(--color-text);
  cursor: pointer;
  display: flex;
  gap: 0.5rem;
  padding: 0.45rem 0.55rem;
  text-align: left;
}

.import-menu button:hover {
  background: var(--color-bg);
}

.source-icon {
  align-items: center;
  background: var(--color-bg);
  border: 1px solid var(--color-border);
  border-radius: 4px;
  color: var(--color-primary);
  display: inline-flex;
  font-size: 0.68rem;
  font-weight: 700;
  height: 24px;
  justify-content: center;
  width: 28px;
}

.dialogue-editor-layout {
  align-items: stretch;
  display: grid;
  gap: 1rem;
  grid-template-columns: minmax(0, 1fr);
}

.speakers-panel {
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  padding: 0.85rem;
}

.speakers-panel-header {
  align-items: center;
  display: flex;
  justify-content: space-between;
}

.speakers-panel-header h3 {
  color: var(--color-primary);
  font-family: var(--font-serif);
  font-size: 1rem;
}

.speakers-panel-header span {
  color: var(--color-text-muted);
  font-size: 0.8rem;
}

.speaker-list {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}

.speaker-item {
  background: var(--color-bg);
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  color: var(--color-text);
  cursor: pointer;
  overflow: hidden;
  padding: 0.45rem 0.55rem;
  text-align: left;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.speaker-item:hover {
  border-color: var(--color-primary);
  color: var(--color-primary);
}

.empty-speakers {
  color: var(--color-text-muted);
  font-size: 0.85rem;
  line-height: 1.5;
}

.speaker-add-form {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  margin-top: auto;
}

.dialogue-step-error {
  margin-top: 1rem;
}

.wizard-nav {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.nav-right {
  display: flex;
  gap: 0.75rem;
}

.author-list {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin-bottom: 0.75rem;
}

.author-chip {
  align-items: center;
  background: var(--color-bg);
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  display: flex;
  gap: 0.75rem;
  justify-content: space-between;
  min-width: 180px;
  padding: 0.5rem 0.65rem;
}

.author-chip div {
  display: flex;
  flex-direction: column;
  gap: 0.1rem;
  min-width: 0;
}

.author-chip strong,
.author-chip span,
.author-chip small {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.author-chip span,
.author-chip small {
  color: var(--color-text-muted);
  font-size: 0.75rem;
}

.chip-remove {
  background: transparent;
  border: 0;
  color: var(--color-text-muted);
  cursor: pointer;
  font-size: 1.2rem;
  line-height: 1;
}

.chip-actions {
  align-items: center;
  display: flex;
  flex-direction: row;
  flex-shrink: 0;
  gap: 0.35rem;
}

.chip-edit {
  background: transparent;
  border: 0;
  color: var(--color-primary);
  cursor: pointer;
  font-size: 0.75rem;
  font-weight: 600;
  padding: 0;
}

.chip-edit:hover,
.chip-remove:hover {
  color: var(--color-primary-dark);
}

.add-author-card {
  align-items: center;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  color: var(--color-primary);
  cursor: pointer;
  display: flex;
  font-weight: 600;
  min-height: 58px;
  padding: 0.5rem 0.75rem;
}

.add-author-card:hover {
  background: var(--color-bg);
}

.illustration-editor,
.illustration-list {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.illustration-edit-row {
  align-items: flex-start;
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  display: grid;
  gap: 0.75rem;
  grid-template-columns: 140px minmax(0, 1fr) auto;
  padding: 0.75rem;
}

.illustration-edit-row img {
  border-radius: var(--radius);
  height: 88px;
  object-fit: cover;
  width: 140px;
}

.illustration-file-name {
  align-items: center;
  background: var(--color-bg);
  border-radius: var(--radius);
  color: var(--color-text-muted);
  display: flex;
  font-size: 0.82rem;
  min-height: 88px;
  overflow-wrap: anywhere;
  padding: 0.75rem;
}

.illustration-edit-row textarea {
  resize: vertical;
}

.illustration-upload {
  align-self: flex-start;
  cursor: pointer;
}

.illustration-upload input {
  display: none;
}

.modal-backdrop {
  align-items: center;
  background: rgba(15, 23, 42, 0.45);
  bottom: 0;
  display: flex;
  justify-content: center;
  left: 0;
  padding: 1rem;
  position: fixed;
  right: 0;
  top: 0;
  z-index: 300;
}

.modal-panel {
  background: var(--color-surface);
  border-radius: var(--radius);
  box-shadow: var(--shadow-lg);
  max-width: 520px;
  padding: 1.25rem;
  width: min(100%, 520px);
}

.modal-header {
  align-items: center;
  display: flex;
  justify-content: space-between;
  margin-bottom: 1rem;
}

.modal-header h2 {
  font-family: var(--font-serif);
  font-size: 1.125rem;
  color: var(--color-primary);
}

.modal-close {
  background: transparent;
  border: 0;
  color: var(--color-text-muted);
  cursor: pointer;
  font-size: 1.4rem;
  line-height: 1;
}

.modal-actions {
  display: flex;
  gap: 0.75rem;
  justify-content: flex-end;
  margin-top: 1rem;
}

@media (max-width: 760px) {
  .dialogue-text-header {
    align-items: stretch;
    flex-direction: column;
  }

  .import-menu {
    left: 0;
    right: auto;
  }

  .dialogue-editor-layout {
    grid-template-columns: 1fr;
  }

  .wizard-nav {
    align-items: stretch;
    flex-direction: column;
    gap: 0.75rem;
  }

  .nav-right {
    justify-content: flex-end;
  }

  .illustration-edit-row {
    grid-template-columns: 1fr;
  }

  .illustration-edit-row img,
  .illustration-file-name {
    width: 100%;
  }
}
</style>
