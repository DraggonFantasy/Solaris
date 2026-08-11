<template>
  <div v-if="dialogue" class="dialogue-page">
    <RouterLink :to="backTarget" class="back-link">← {{ t('common.back') }}</RouterLink>

    <header class="dialogue-header">
      <div class="dialogue-section-tag">{{ dialogue.section_name }}</div>
      <h1 class="dialogue-title">{{ dialogue.title }}</h1>
      <div class="dialogue-meta">
        <span v-if="dialogue.human_author_username">{{ t('dialogues.by') }}: <strong>{{ dialogue.human_author_username }}</strong></span>
        <span v-if="dialogue.llm_name">{{ t('dialogues.model') }}: <strong>{{ dialogue.llm_name }} {{ dialogue.llm_version }}</strong></span>
        <span>{{ formatDate(dialogue.created_at) }}</span>
      </div>
      <div v-if="dialogue.authors?.length" class="dialogue-authors">
        <span v-for="author in dialogue.authors" :key="`${author.kind}-${author.name}`" class="author-pill">
          {{ author.name }}<small v-if="author.version"> {{ author.version }}</small>
        </span>
      </div>
      <div v-if="canEdit" class="dialogue-actions">
        <RouterLink class="btn btn-outline" :to="{ name: 'edit-dialogue', params: { id: dialogue.id } }">
          {{ t('dialogue.edit') }}
        </RouterLink>
        <button
          v-if="canDelete"
          class="btn btn-danger"
          type="button"
          :disabled="deleting"
          @click="deleteDialogue"
        >
          {{ deleting ? t('common.loading') : t('dialogue.delete') }}
        </button>
      </div>
      <div v-else-if="canWithdraw" class="dialogue-actions">
        <button class="btn btn-outline" :disabled="withdrawing" @click="withdrawFromReview">
          {{ withdrawing ? t('common.loading') : t('dialogue.withdrawReview') }}
        </button>
      </div>
      <div v-if="dialogueActionError" class="alert alert-error dialogue-action-error">
        {{ dialogueActionError }}
      </div>
    </header>

    <div v-if="dialogue.moderation_note" class="moderation-message">
      <h2>{{ t('dialogue.moderationMessage') }}</h2>
      <p>{{ dialogue.moderation_note }}</p>
    </div>

    <form v-if="auth.isStaff" class="staff-status-panel card" @submit.prevent="updateDialogueStatus">
      <div class="staff-status-main">
        <label>
          {{ t('moderation.statusLabel') }}
          <select v-model="statusDraft">
            <option v-for="status in moderationStatuses" :key="status" :value="status">
              {{ t(`dialogue.status.${status}`) }}
            </option>
          </select>
        </label>
        <label>
          {{ t('dialogue.moderationMessage') }}
          <textarea
            v-model="moderationNoteDraft"
            rows="2"
            :placeholder="statusDraft === 'changes_requested' ? t('moderation.changesNotePlaceholder') : t('moderation.notePlaceholder')"
          />
        </label>
      </div>
      <button class="btn btn-primary btn-sm" type="submit" :disabled="savingStatus">
        {{ savingStatus ? t('common.loading') : t('common.save') }}
      </button>
    </form>

    <div v-if="dialogue.summary" class="dialogue-block">
      <h2>{{ t('dialogues.summary') }}</h2>
      <p>{{ dialogue.summary }}</p>
    </div>

    <div v-if="dialogue.illustrations?.length" class="dialogue-block">
      <h2>{{ t('dialogues.illustrations') }}</h2>
      <div class="illustrations-menu">
        <nav class="illustration-tabs" :aria-label="t('dialogues.illustrations')">
          <button
            v-for="(ill, index) in dialogue.illustrations"
            :key="ill.id"
            type="button"
            :class="{ active: selectedIllustration?.id === ill.id }"
            @click="activeIllustrationId = ill.id"
          >
            {{ illustrationMenuLabel(ill, index) }}
          </button>
        </nav>
        <figure v-if="selectedIllustration" class="illustration-detail">
          <button type="button" class="illustration-preview" @click="openIllustrationModal(selectedIllustration)">
            <img :src="selectedIllustration.image" :alt="selectedIllustration.caption" />
          </button>
          <figcaption v-if="selectedIllustration.caption">{{ selectedIllustration.caption }}</figcaption>
        </figure>
      </div>
    </div>

    <div v-if="dialogue.text" class="dialogue-text card">
      <MarkdownRenderer :content="dialogue.text" />
    </div>
    <div v-else class="dialogue-text external-dialogue-card card">
      <p>{{ t('dialogue.externalOnly') }}</p>
      <a
        v-if="dialogue.source_url"
        class="btn btn-outline"
        :href="dialogue.source_url"
        target="_blank"
        rel="noopener noreferrer"
      >
        {{ t('dialogue.openExternal') }} ↗
      </a>
    </div>

    <div v-if="dialogue.food_for_thought" class="dialogue-block">
      <h2>{{ t('dialogues.foodForThought') }}</h2>
      <p>{{ dialogue.food_for_thought }}</p>
    </div>

    <div v-if="dialogue.recommended_literature" class="dialogue-block">
      <h2>{{ t('dialogues.literature') }}</h2>
      <p>{{ dialogue.recommended_literature }}</p>
    </div>

    <!-- Like button -->
    <div v-if="isPublished" class="like-row">
      <button class="btn" :class="dialogue.user_has_liked ? 'btn-primary' : 'btn-outline'" @click="toggleLike">
        ♥ {{ dialogue.likes_count }}
      </button>
    </div>

    <DialogueComments
      v-if="isPublished"
      :dialogue="dialogue"
      anchor-id="comments"
      @updated="setDialogue"
    />

    <div v-if="modalIllustration" class="illustration-modal" role="dialog" aria-modal="true" @click.self="closeIllustrationModal">
      <div class="illustration-modal-content">
        <button type="button" class="illustration-modal-close" :aria-label="t('common.close')" @click="closeIllustrationModal">
          ×
        </button>
        <img :src="modalIllustration.image" :alt="modalIllustration.caption" />
        <p v-if="modalIllustration.caption">{{ modalIllustration.caption }}</p>
      </div>
    </div>
  </div>

  <div v-else-if="loading" class="text-muted">{{ t('common.loading') }}</div>
  <div v-else class="detail-error card">
    <h1>{{ detailErrorTitle }}</h1>
    <p>{{ detailErrorText }}</p>
    <RouterLink class="btn btn-primary" to="/sections">{{ t('sections.title') }}</RouterLink>
  </div>
</template>

<script setup>
import { computed, ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useAuthStore } from '../stores/auth'
import api from '../api'
import DialogueComments from '../components/DialogueComments.vue'
import MarkdownRenderer from '../components/MarkdownRenderer.vue'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const dialogue = ref(null)
const loading = ref(true)
const detailErrorStatus = ref(null)
const dialogueActionError = ref('')
const withdrawing = ref(false)
const deleting = ref(false)
const savingStatus = ref(false)
const statusDraft = ref('')
const moderationNoteDraft = ref('')
const activeIllustrationId = ref(null)
const modalIllustration = ref(null)

const moderationStatuses = ['submitted', 'changes_requested', 'rejected', 'published', 'archived']

const isPublished = computed(() => dialogue.value?.status === 'published')
const canEdit = computed(() => {
  if (!dialogue.value || !auth.isAuthenticated) return false
  return auth.isStaff || ['draft', 'changes_requested', 'rejected'].includes(dialogue.value.status)
})
const canDelete = computed(() => canEdit.value)
const canWithdraw = computed(() => {
  return auth.isAuthenticated && dialogue.value?.status === 'submitted'
})
const backTarget = computed(() => {
  if (!dialogue.value) return { name: 'sections' }
  if (dialogue.value.status !== 'published') return { name: 'my-dialogues' }
  return `/sections/${dialogue.value.section_slug}`
})
const selectedIllustration = computed(() => {
  const illustrations = dialogue.value?.illustrations || []
  if (!illustrations.length) return null
  return illustrations.find((illustration) => illustration.id === activeIllustrationId.value) || illustrations[0]
})

onMounted(async () => {
  try {
    const { data } = await api.get(`/dialogues/${route.params.id}/`)
    setDialogue(data)
  } catch (err) {
    detailErrorStatus.value = err.response?.status || 0
  } finally {
    loading.value = false
  }
})

const detailErrorTitle = computed(() => {
  if (detailErrorStatus.value === 403 || detailErrorStatus.value === 404) {
    return t('dialogue.notAvailableTitle')
  }
  return t('common.error')
})

const detailErrorText = computed(() => {
  if (detailErrorStatus.value === 403 || detailErrorStatus.value === 404) {
    return t('dialogue.notAvailableText')
  }
  return t('dialogue.loadErrorText')
})

function setDialogue(data) {
  dialogue.value = data
  statusDraft.value = data.status || 'submitted'
  moderationNoteDraft.value = data.moderation_note || ''
  activeIllustrationId.value = data.illustrations?.[0]?.id || null
  modalIllustration.value = null
}

function formatDate(iso) {
  return new Date(iso).toLocaleDateString()
}

function openIllustrationModal(illustration) {
  modalIllustration.value = illustration
}

function closeIllustrationModal() {
  modalIllustration.value = null
}

function illustrationMenuLabel(illustration, index) {
  const fallback = `${t('dialogues.illustrations')} ${index + 1}`
  const caption = (illustration.caption || '').trim()
  if (!caption) return fallback
  return caption.length > 64 ? `${caption.slice(0, 61).trim()}...` : caption
}

async function toggleLike() {
  if (!auth.isAuthenticated || !isPublished.value) return
  const { data } = await api.post(`/dialogues/${route.params.id}/like/`)
  dialogue.value.user_has_liked = data.liked
  dialogue.value.likes_count = data.likes_count
}

async function withdrawFromReview() {
  if (!canWithdraw.value) return
  dialogueActionError.value = ''
  withdrawing.value = true
  try {
    const { data } = await api.post(`/dialogues/${route.params.id}/withdraw/`)
    setDialogue(data)
  } catch {
    dialogueActionError.value = t('common.error')
  } finally {
    withdrawing.value = false
  }
}

async function deleteDialogue() {
  if (!canDelete.value || !window.confirm(t('dialogue.deleteConfirm'))) return
  dialogueActionError.value = ''
  deleting.value = true
  try {
    await api.delete(`/dialogues/${route.params.id}/`)
    router.push(auth.isStaff ? { name: 'communications' } : { name: 'my-dialogues' })
  } catch {
    dialogueActionError.value = t('dialogue.deleteError')
  } finally {
    deleting.value = false
  }
}

async function updateDialogueStatus() {
  dialogueActionError.value = ''
  savingStatus.value = true
  try {
    const { data } = await api.post(`/dialogues/${route.params.id}/moderate/`, {
      status: statusDraft.value,
      moderation_note: moderationNoteDraft.value,
    })
    setDialogue({
      ...dialogue.value,
      status: data.status,
      moderation_note: data.moderation_note,
      published: data.status === 'published',
    })
  } catch {
    dialogueActionError.value = t('common.error')
  } finally {
    savingStatus.value = false
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

.detail-error {
  margin: 3rem auto;
  max-width: 560px;
  padding: 2rem;
}

.detail-error h1 {
  font-family: var(--font-serif);
  font-size: 1.6rem;
  margin-bottom: 0.75rem;
}

.detail-error p {
  color: var(--color-text-muted);
  line-height: 1.6;
  margin-bottom: 1.25rem;
}

.dialogue-header {
  margin-bottom: 2rem;
}

.dialogue-section-tag {
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--color-accent);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin-bottom: 0.5rem;
}

.dialogue-title {
  font-family: var(--font-serif);
  font-size: 2rem;
  line-height: 1.3;
  margin-bottom: 1rem;
}

.dialogue-meta {
  display: flex;
  gap: 1.5rem;
  font-size: 0.875rem;
  color: var(--color-text-muted);
}

.dialogue-authors {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin-top: 0.9rem;
}

.author-pill {
  background: var(--color-bg);
  border: 1px solid var(--color-border);
  border-radius: 999px;
  color: var(--color-text);
  font-size: 0.78rem;
  padding: 0.25rem 0.6rem;
}

.author-pill small {
  color: var(--color-text-muted);
}

.dialogue-actions {
  display: flex;
  gap: 0.75rem;
  margin-top: 1rem;
}

.dialogue-action-error {
  margin-top: 1rem;
}

.staff-status-panel {
  align-items: flex-end;
  display: grid;
  gap: 1rem;
  grid-template-columns: minmax(0, 1fr) auto;
  margin: 1.5rem 0;
}

.staff-status-main {
  display: grid;
  gap: 0.75rem;
  grid-template-columns: 220px minmax(0, 1fr);
}

.staff-status-panel label {
  color: var(--color-text-muted);
  display: flex;
  flex-direction: column;
  font-size: 0.78rem;
  font-weight: 600;
  gap: 0.35rem;
}

.staff-status-panel select,
.staff-status-panel textarea {
  color: var(--color-text);
  font: inherit;
}

.staff-status-panel textarea {
  resize: vertical;
}

.moderation-message {
  background: #fef9c3;
  border: 1px solid #fde68a;
  border-radius: var(--radius);
  color: #713f12;
  margin: 1.5rem 0;
  padding: 1rem;
}

.moderation-message h2 {
  font-family: var(--font-serif);
  font-size: 1rem;
  margin-bottom: 0.5rem;
}

.moderation-message p {
  line-height: 1.6;
  white-space: pre-wrap;
}

.dialogue-block {
  margin: 1.5rem 0;
}

.dialogue-block h2 {
  font-family: var(--font-serif);
  font-size: 1.125rem;
  margin-bottom: 0.75rem;
  color: var(--color-primary);
}

.dialogue-text {
  margin: 1.5rem 0;
}

.external-dialogue-card {
  align-items: center;
  display: flex;
  flex-wrap: wrap;
  gap: 1rem;
  justify-content: space-between;
}

.external-dialogue-card p {
  color: var(--color-text);
  line-height: 1.6;
  margin: 0;
}


.like-row {
  margin: 1.5rem 0;
}

.illustrations-menu {
  display: grid;
  gap: 1rem;
  grid-template-columns: 240px minmax(0, 420px);
  align-items: start;
}

.illustration-tabs {
  border-right: 1px solid var(--color-border);
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
  padding-right: 0.75rem;
}

.illustration-tabs button {
  background: transparent;
  border: 0;
  border-radius: var(--radius);
  color: var(--color-text-muted);
  cursor: pointer;
  font: inherit;
  padding: 0.55rem 0.65rem;
  text-align: left;
}

.illustration-tabs button:hover,
.illustration-tabs button.active {
  background: var(--color-bg);
  color: var(--color-primary);
}

.illustration-detail {
  margin: 0;
}

.illustration-preview {
  align-items: center;
  background: var(--color-bg);
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  cursor: zoom-in;
  display: flex;
  height: 220px;
  justify-content: center;
  padding: 0;
  width: 100%;
}

.illustration-preview img {
  display: block;
  max-height: 100%;
  max-width: 100%;
  object-fit: contain;
  border-radius: var(--radius);
}

.illustration-detail figcaption {
  font-size: 0.9rem;
  color: var(--color-text-muted);
  line-height: 1.6;
  margin-top: 0.75rem;
  white-space: pre-wrap;
}

.illustration-modal {
  align-items: center;
  background: rgba(17, 24, 39, 0.72);
  display: flex;
  inset: 0;
  justify-content: center;
  padding: 1.5rem;
  position: fixed;
  z-index: 200;
}

.illustration-modal-content {
  background: var(--color-surface);
  border-radius: var(--radius);
  box-shadow: 0 24px 80px rgba(17, 24, 39, 0.35);
  max-height: calc(100vh - 3rem);
  max-width: min(920px, calc(100vw - 3rem));
  overflow: auto;
  padding: 1rem;
  position: relative;
}

.illustration-modal-close {
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
  position: absolute;
  right: 0.75rem;
  top: 0.75rem;
  width: 2rem;
}

.illustration-modal-content img {
  display: block;
  max-height: calc(100vh - 8rem);
  max-width: 100%;
  object-fit: contain;
}

.illustration-modal-content p {
  color: var(--color-text-muted);
  line-height: 1.6;
  margin: 0.75rem 2.5rem 0 0;
  white-space: pre-wrap;
}

@media (max-width: 760px) {
  .illustrations-menu {
    grid-template-columns: 1fr;
  }

  .illustration-tabs {
    border-right: 0;
    border-bottom: 1px solid var(--color-border);
    padding: 0 0 0.75rem;
  }

  .illustration-preview {
    height: 180px;
  }
}
</style>
