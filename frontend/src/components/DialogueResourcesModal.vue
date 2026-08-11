<template>
  <Teleport to="body">
    <div v-if="open" class="resource-modal" role="dialog" aria-modal="true" @click.self="close">
      <div class="resource-modal-content card">
        <header class="resource-modal-header">
          <div>
            <h2>{{ typeLabel }}</h2>
            <p>{{ dialogue?.title }}</p>
          </div>
          <button type="button" class="resource-modal-close" :aria-label="t('common.close')" @click="close">
            ×
          </button>
        </header>

        <div class="resource-modal-body">
          <div v-if="loading" class="text-muted">{{ t('common.loading') }}</div>
          <div v-else-if="loadError" class="alert alert-error">{{ loadError }}</div>

          <template v-else-if="detail">
            <DialogueComments
              v-if="type === 'comments'"
              :dialogue="detail"
              :show-title="false"
              compact
              @updated="updateDialogue"
            />

            <template v-else>
          <div v-if="currentItems.length" class="resource-list">
            <article
              v-for="(item, index) in currentItems"
              :key="item.id || itemKey(item, index)"
              class="resource-item"
            >
              <template v-if="type === 'authors' || type === 'ai_model'">
                <h3>
                  {{ item.name }}
                  <small v-if="item.version">{{ item.version }}</small>
                </h3>
                <span v-if="type === 'authors'" class="resource-kind">{{ authorKindLabel(item.kind) }}</span>
                <p v-if="item.description">{{ item.description }}</p>
              </template>

              <p v-else-if="type === 'literature'" class="pre-line">{{ item.text }}</p>

              <figure v-else-if="type === 'illustrations'" class="illustration-item">
                <img :src="item.image" :alt="item.caption" />
                <figcaption v-if="item.caption">{{ item.caption }}</figcaption>
              </figure>
            </article>
          </div>
          <p v-else class="text-muted resource-empty">{{ t('sections.noResources') }}</p>

          <section v-if="pendingItems.length" class="pending-section">
            <h3>{{ t('resources.pendingTitle') }}</h3>
            <article v-for="proposal in pendingItems" :key="proposal.id" class="pending-item">
              <span class="pending-badge">{{ t('resources.pending') }}</span>
              <template v-if="proposal.resource_type === 'illustration'">
                <img v-if="proposal.image" :src="proposal.image" :alt="proposal.payload.caption || ''" />
                <p v-if="proposal.payload.caption">{{ proposal.payload.caption }}</p>
              </template>
              <template v-else-if="proposal.resource_type === 'literature'">
                <p>{{ proposal.payload.text }}</p>
              </template>
              <template v-else>
                <strong>{{ proposal.payload.name }}</strong>
                <small v-if="proposal.payload.version">{{ proposal.payload.version }}</small>
                <small v-if="proposal.resource_type === 'author'">
                  {{ authorKindLabel(proposal.payload.kind) }}
                </small>
                <p v-if="proposal.payload.description">{{ proposal.payload.description }}</p>
              </template>
            </article>
          </section>

          <div v-if="submitNotice" class="alert alert-success">{{ submitNotice }}</div>
          <div v-if="submitError" class="alert alert-error">{{ submitError }}</div>

          <button
            v-if="auth.isAuthenticated && !showForm"
            class="btn btn-primary add-resource-button"
            type="button"
            @click="openForm"
          >
            + {{ addLabel }}
          </button>

          <form v-else-if="auth.isAuthenticated" class="resource-form" @submit.prevent="submitProposal">
            <template v-if="type === 'authors'">
              <label class="form-group">
                <span>{{ t('dialogue.authorType') }}</span>
                <select v-model="draft.kind">
                  <option value="person">{{ t('dialogue.authorKindPerson') }}</option>
                  <option value="organization">{{ t('dialogue.authorKindOrganization') }}</option>
                </select>
              </label>
              <label class="form-group">
                <span>{{ t('dialogue.authorName') }}</span>
                <input v-model.trim="draft.name" type="text" required />
              </label>
              <label class="form-group">
                <span>{{ t('dialogue.authorVersion') }}</span>
                <input v-model.trim="draft.version" type="text" />
              </label>
              <label class="form-group">
                <span>{{ t('dialogue.authorDescription') }}</span>
                <textarea v-model.trim="draft.description" rows="3" />
              </label>
            </template>

            <template v-else-if="type === 'ai_model'">
              <label class="form-group">
                <span>{{ t('resources.modelName') }}</span>
                <input v-model.trim="draft.name" type="text" required />
              </label>
              <label class="form-group">
                <span>{{ t('dialogue.authorVersion') }}</span>
                <input v-model.trim="draft.version" type="text" />
              </label>
              <label class="form-group">
                <span>{{ t('dialogue.authorDescription') }}</span>
                <textarea v-model.trim="draft.description" rows="3" />
              </label>
            </template>

            <label v-else-if="type === 'literature'" class="form-group">
              <span>{{ t('resources.literatureText') }}</span>
              <textarea v-model.trim="draft.text" rows="5" required />
            </label>

            <template v-else-if="type === 'illustrations'">
              <label class="form-group">
                <span>{{ t('resources.image') }}</span>
                <input ref="fileInput" type="file" accept="image/*" required @change="selectImage" />
              </label>
              <label class="form-group">
                <span>{{ t('resources.caption') }}</span>
                <textarea v-model.trim="draft.caption" rows="3" />
              </label>
            </template>

            <footer class="resource-form-actions">
              <button class="btn btn-primary" type="submit" :disabled="submitting || !canSubmit">
                {{ submitting ? t('common.loading') : t('resources.sendForReview') }}
              </button>
              <button class="btn btn-outline" type="button" :disabled="submitting" @click="closeForm">
                {{ t('common.cancel') }}
              </button>
            </footer>
          </form>

          <RouterLink
            v-else
            class="btn btn-outline add-resource-button"
            :to="{ name: 'login', query: { redirect: route.fullPath } }"
          >
            {{ t('resources.loginToAdd') }}
          </RouterLink>
            </template>
          </template>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { computed, nextTick, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useAuthStore } from '../stores/auth'
import api from '../api'
import DialogueComments from './DialogueComments.vue'

const props = defineProps({
  open: { type: Boolean, default: false },
  type: { type: String, default: 'authors' },
  dialogue: { type: Object, default: null },
})

const emit = defineEmits(['close', 'updated'])
const { t } = useI18n()
const route = useRoute()
const auth = useAuthStore()
const detail = ref(null)
const pendingItems = ref([])
const loading = ref(false)
const loadError = ref('')
const submitError = ref('')
const submitNotice = ref('')
const submitting = ref(false)
const showForm = ref(false)
const selectedFile = ref(null)
const fileInput = ref(null)
const draft = ref(emptyDraft())

const labels = computed(() => ({
  authors: t('dialogues.by'),
  literature: t('dialogues.literature'),
  comments: t('dialogues.comments'),
  illustrations: t('dialogues.illustrations'),
  ai_model: t('dialogues.aiModel'),
}))

const addLabels = computed(() => ({
  authors: t('dialogue.addAuthor'),
  literature: t('resources.addLiterature'),
  comments: t('dialogues.addComment'),
  illustrations: t('dialogue.addIllustration'),
  ai_model: t('resources.addModel'),
}))

const typeLabel = computed(() => labels.value[props.type] || '')
const addLabel = computed(() => addLabels.value[props.type] || '')
const proposalType = computed(() => props.type === 'authors' ? 'author' : props.type.replace(/s$/, ''))

const authorItems = computed(() => {
  const authors = Array.isArray(detail.value?.authors) ? detail.value.authors : []
  const items = authors.filter((author) => author?.kind !== 'ai_model' && author?.name)
  if (!items.length && detail.value?.human_author_username) {
    return [{ kind: 'person', name: detail.value.human_author_username }]
  }
  return items
})

const modelItems = computed(() => {
  const authors = Array.isArray(detail.value?.authors) ? detail.value.authors : []
  const models = authors.filter((author) => author?.kind === 'ai_model' && author?.name)
  if (detail.value?.llm_name && !models.some((model) => model.name === detail.value.llm_name)) {
    models.unshift({
      kind: 'ai_model',
      name: detail.value.llm_name,
      version: detail.value.llm_version || '',
    })
  }
  return models
})

const literatureItems = computed(() => {
  const text = detail.value?.recommended_literature?.trim()
  if (!text) return []
  return text.split(/\n\s*\n/).filter(Boolean).map((item) => ({ text: item.trim() }))
})

const currentItems = computed(() => {
  if (props.type === 'authors') return authorItems.value
  if (props.type === 'ai_model') return modelItems.value
  if (props.type === 'literature') return literatureItems.value
  if (props.type === 'illustrations') return detail.value?.illustrations || []
  return []
})

const canSubmit = computed(() => {
  if (props.type === 'authors' || props.type === 'ai_model') return Boolean(draft.value.name.trim())
  if (props.type === 'literature') return Boolean(draft.value.text.trim())
  if (props.type === 'illustrations') return Boolean(selectedFile.value)
  return false
})

watch(
  () => [props.open, props.dialogue?.id, props.type],
  ([open]) => {
    if (open && props.dialogue?.id) loadDialogue()
  },
  { immediate: true },
)

function emptyDraft() {
  return {
    kind: 'person',
    name: '',
    version: '',
    description: '',
    text: '',
    caption: '',
  }
}

async function loadDialogue() {
  loading.value = true
  loadError.value = ''
  submitError.value = ''
  submitNotice.value = ''
  closeForm()
  try {
    const requests = [api.get(`/dialogues/${props.dialogue.id}/`)]
    if (auth.isAuthenticated && props.type !== 'comments') {
      requests.push(api.get(`/dialogues/${props.dialogue.id}/resource-proposals/`))
    }
    const [dialogueResponse, proposalResponse] = await Promise.all(requests)
    detail.value = dialogueResponse.data
    const proposals = proposalResponse
      ? (proposalResponse.data.results || proposalResponse.data)
      : []
    pendingItems.value = proposals.filter((proposal) => proposal.resource_type === proposalType.value)
  } catch {
    loadError.value = t('common.error')
  } finally {
    loading.value = false
  }
}

function updateDialogue(value) {
  detail.value = value
  emit('updated', value)
}

function itemKey(item, index) {
  return `${item.kind || props.type}-${item.name || item.text || ''}-${item.version || ''}-${index}`
}

function authorKindLabel(kind) {
  if (kind === 'organization') return t('dialogue.authorKindOrganization')
  return t('dialogue.authorKindPerson')
}

function openForm() {
  submitError.value = ''
  submitNotice.value = ''
  showForm.value = true
  if (props.type === 'illustrations') {
    nextTick(() => fileInput.value?.focus())
  }
}

function closeForm() {
  showForm.value = false
  selectedFile.value = null
  draft.value = emptyDraft()
  if (fileInput.value) fileInput.value.value = ''
}

function selectImage(event) {
  selectedFile.value = event.target.files?.[0] || null
}

async function submitProposal() {
  if (!canSubmit.value || !detail.value) return
  submitting.value = true
  submitError.value = ''
  submitNotice.value = ''
  try {
    let body
    if (props.type === 'illustrations') {
      body = new FormData()
      body.append('resource_type', 'illustration')
      body.append('image', selectedFile.value)
      body.append('caption', draft.value.caption)
    } else if (props.type === 'literature') {
      body = { resource_type: 'literature', text: draft.value.text }
    } else {
      body = {
        resource_type: proposalType.value,
        name: draft.value.name,
        version: draft.value.version,
        description: draft.value.description,
      }
      if (props.type === 'authors') body.kind = draft.value.kind
    }

    const { data } = await api.post(
      `/dialogues/${detail.value.id}/resource-proposals/`,
      body,
    )
    pendingItems.value.push(data)
    closeForm()
    submitNotice.value = t('resources.sentForReview')
  } catch (error) {
    const responseData = error.response?.data
    const firstError = typeof responseData === 'string'
      ? responseData
      : responseData && Object.values(responseData).flat()[0]
    submitError.value = firstError || t('resources.submitError')
  } finally {
    submitting.value = false
  }
}

function close() {
  if (submitting.value) return
  emit('close')
}
</script>

<style scoped>
.resource-modal {
  align-items: center;
  background: rgba(17, 24, 39, 0.72);
  display: flex;
  inset: 0;
  justify-content: center;
  padding: clamp(0.75rem, 2vw, 1.5rem);
  position: fixed;
  z-index: 200;
}

.resource-modal-content {
  display: flex;
  flex-direction: column;
  max-height: calc(100vh - 3rem);
  max-height: min(760px, 85dvh);
  max-width: min(760px, calc(100vw - 3rem));
  overflow: hidden;
  padding: 0;
  width: 100%;
}

.resource-modal-close {
  align-items: center;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: 999px;
  cursor: pointer;
  display: flex;
  font-size: 1.25rem;
  height: 2rem;
  justify-content: center;
  line-height: 1;
  flex: 0 0 2rem;
  width: 2rem;
}

.resource-modal-header {
  align-items: flex-start;
  border-bottom: 1px solid var(--color-border);
  display: flex;
  flex: 0 0 auto;
  gap: 1rem;
  justify-content: space-between;
  padding: 1.25rem 1.5rem;
}

.resource-modal-header > div {
  min-width: 0;
}

.resource-modal-header h2 {
  color: var(--color-primary);
  font-family: var(--font-serif);
  font-size: 1.35rem;
  margin-bottom: 0.25rem;
}

.resource-modal-header p {
  color: var(--color-text-muted);
  font-size: 0.86rem;
  line-height: 1.45;
  overflow-wrap: anywhere;
}

.resource-modal-body {
  min-height: 0;
  overflow-y: auto;
  overscroll-behavior: contain;
  padding: 1.5rem;
  scrollbar-gutter: stable;
}

.resource-list {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.resource-item {
  border-bottom: 1px solid var(--color-border);
  padding-bottom: 1rem;
}

.resource-item:last-child {
  border-bottom: 0;
}

.resource-item h3 {
  font-family: var(--font-serif);
  font-size: 1rem;
  margin-bottom: 0.25rem;
}

.resource-item small,
.pending-item small {
  color: var(--color-text-muted);
  font-size: 0.78rem;
  margin-left: 0.35rem;
}

.resource-item p,
.pending-item p {
  color: var(--color-text-muted);
  line-height: 1.6;
  white-space: pre-wrap;
}

.resource-kind {
  color: var(--color-accent);
  display: block;
  font-size: 0.75rem;
  margin-bottom: 0.3rem;
}

.resource-empty {
  margin-bottom: 1.25rem;
}

.illustration-item {
  margin: 0;
}

.illustration-item img {
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  display: block;
  max-height: 320px;
  max-width: 100%;
  object-fit: contain;
}

.illustration-item figcaption {
  color: var(--color-text-muted);
  font-size: 0.84rem;
  margin-top: 0.5rem;
}

.pending-section {
  background: var(--color-bg);
  border-radius: var(--radius);
  margin: 1.25rem 0;
  padding: 1rem;
}

.pending-section h3 {
  font-size: 0.9rem;
  margin-bottom: 0.75rem;
}

.pending-item {
  border-bottom: 1px solid var(--color-border);
  padding: 0.65rem 0;
}

.pending-item:last-child {
  border-bottom: 0;
}

.pending-item img {
  display: block;
  margin-top: 0.5rem;
  max-height: 160px;
  max-width: 100%;
}

.pending-badge {
  background: #fef3c7;
  border-radius: 999px;
  color: #92400e;
  display: inline-block;
  font-size: 0.7rem;
  font-weight: 600;
  margin-bottom: 0.45rem;
  padding: 0.1rem 0.45rem;
}

.add-resource-button {
  margin-top: 1.25rem;
}

.resource-form {
  border-top: 1px solid var(--color-border);
  margin-top: 1.25rem;
  padding-top: 1.25rem;
}

.resource-form .form-group span {
  display: block;
  font-size: 0.85rem;
  font-weight: 600;
  margin-bottom: 0.4rem;
}

.resource-form-actions {
  display: flex;
  gap: 0.75rem;
  margin-top: 1rem;
}

@media (max-width: 600px) {
  .resource-modal-content {
    max-width: calc(100vw - 1.5rem);
  }

  .resource-modal-header,
  .resource-modal-body {
    padding: 1rem;
  }
}
</style>
