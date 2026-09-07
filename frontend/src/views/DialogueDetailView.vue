<template>
  <div v-if="dialogue" class="dialogue-page">
    <BackLink :fallback="backTarget" />

    <header class="dialogue-header">
      <div class="dialogue-section-tag">{{ dialogue.section_name }}</div>
      <h1 class="dialogue-title">{{ dialogue.title }}</h1>
      <div class="dialogue-meta">
        <span v-if="dialogue.human_author_username">{{ t('dialogues.by') }}: <strong>{{ dialogue.human_author_username }}</strong></span>
        <span v-if="dialogue.llm_name">{{ t('dialogues.model') }}: <strong>{{ dialogue.llm_name }} {{ dialogue.llm_version }}</strong></span>
        <span>{{ t('dialogue.publicationDate') }}: <strong>{{ formatDate(dialogue.published_at || dialogue.created_at) }}</strong></span>
        <span class="dialogue-status" :class="dialogue.status">{{ t(`dialogue.status.${dialogue.status}`) }}</span>
      </div>
      <p v-if="dialogue.human_author_bio" class="author-profile">{{ dialogue.human_author_bio }}</p>
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
          v-if="canArchive"
          class="btn btn-outline"
          type="button"
          :disabled="archiving"
          @click="archiveDialogue"
        >
          {{ archiving ? t('common.loading') : t('moderation.archive') }}
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

    <nav v-if="isPublished" class="dialogue-resource-actions">
      <button class="btn btn-outline btn-sm" @click="openResource('authors')">{{ t('dialogues.by') }}</button>
      <button class="btn btn-outline btn-sm" @click="openResource('literature')">{{ t('dialogues.literature') }}</button>
      <button class="btn btn-outline btn-sm" @click="openResource('comments')">{{ t('dialogues.comments') }}</button>
      <button class="btn btn-outline btn-sm" @click="openResource('illustrations')">{{ t('dialogues.illustrations') }}</button>
      <button class="btn btn-outline btn-sm" @click="openResource('ai_model')">{{ t('dialogues.aiModel') }}</button>
    </nav>

    <DialogueImportWarning :error="dialogue.import_error" />

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

    <div v-if="firstIllustration" class="dialogue-block">
      <h2>{{ t('dialogues.illustrations') }}</h2>
      <div class="illustrations-menu single-illustration">
        <figure class="illustration-detail">
          <button type="button" class="illustration-preview" @click="openIllustrationModal(firstIllustration)">
            <img :src="firstIllustration.image" :alt="firstIllustration.caption" />
          </button>
          <figcaption v-if="firstIllustration.caption">
            {{ illustrationCaptionExpanded ? firstIllustration.caption : shortIllustrationCaption }}
            <button v-if="illustrationCaptionTruncated" type="button" class="text-toggle" @click="illustrationCaptionExpanded = !illustrationCaptionExpanded">
              {{ illustrationCaptionExpanded ? t('dialogue.showLess') : t('dialogue.showMore') }}
            </button>
          </figcaption>
        </figure>
      </div>
    </div>

    <section v-if="dialogue.text || dialogue.source_url" class="dialogue-access card">
      <h2>{{ t('dialogue.accessTitle') }}</h2>
      <div class="dialogue-access-options">
        <div v-if="dialogue.text?.trim()" class="dialogue-access-option">
          <p>{{ t('dialogue.internalStored') }}</p>
          <RouterLink class="btn btn-primary" :to="{ name: 'dialogue-reader', params: { id: dialogue.id } }">
            {{ t('dialogue.openInternal') }}
          </RouterLink>
        </div>
        <div v-if="dialogue.source_url" class="dialogue-access-option">
          <p>{{ t('dialogue.externalStored') }}</p>
          <a
            class="btn btn-outline"
            :href="dialogue.source_url"
            target="_blank"
            rel="noopener noreferrer"
          >
            {{ t('dialogue.openExternal') }} ↗
          </a>
        </div>
      </div>
    </section>

    <div v-if="dialogue.food_for_thought" class="dialogue-block">
      <h2>{{ t('dialogues.foodForThought') }}</h2>
      <p>{{ dialogue.food_for_thought }}</p>
    </div>

    <div v-if="dialogue.literature?.length || dialogue.recommended_literature" class="dialogue-block">
      <h2>{{ t('dialogues.literature') }}</h2>
      <article v-for="item in dialogue.literature" :key="item.id" class="literature-item">
        <strong>{{ item.title }}</strong>
        <span v-if="item.author">{{ item.author }}</span>
        <p v-if="item.annotation">{{ item.annotation }}</p>
        <a v-if="item.url" :href="item.url" target="_blank" rel="noopener noreferrer">{{ item.url }}</a>
      </article>
      <p v-if="!dialogue.literature?.length">{{ dialogue.recommended_literature }}</p>
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

    <DialogueResourcesModal
      :open="resourceModal.open"
      :type="resourceModal.type"
      :dialogue="dialogue"
      @close="resourceModal.open = false"
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
import DialogueImportWarning from '../components/DialogueImportWarning.vue'
import DialogueResourcesModal from '../components/DialogueResourcesModal.vue'
import BackLink from '../components/BackLink.vue'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const dialogue = ref(null)
const loading = ref(true)
const detailErrorStatus = ref(null)
const dialogueActionError = ref('')
const withdrawing = ref(false)
const archiving = ref(false)
const savingStatus = ref(false)
const statusDraft = ref('')
const moderationNoteDraft = ref('')
const modalIllustration = ref(null)
const illustrationCaptionExpanded = ref(false)
const resourceModal = ref({ open: false, type: 'authors' })

const moderationStatuses = ['submitted', 'changes_requested', 'rejected', 'published', 'archived']

const isPublished = computed(() => dialogue.value?.status === 'published')
const canEdit = computed(() => {
  if (!dialogue.value || !auth.isAuthenticated) return false
  return auth.isStaff || ['draft', 'changes_requested', 'rejected'].includes(dialogue.value.status)
})
const canArchive = computed(() => auth.isStaff && dialogue.value?.status !== 'archived')
const canWithdraw = computed(() => {
  return auth.isAuthenticated && dialogue.value?.status === 'submitted'
})
const backTarget = computed(() => {
  if (!dialogue.value) return { name: 'sections' }
  if (dialogue.value.status === 'archived' && auth.isStaff) return { name: 'archive' }
  if (dialogue.value.status !== 'published' && auth.isStaff) return { name: 'communications' }
  if (dialogue.value.status !== 'published') return { name: 'my-dialogues' }
  return `/sections/${dialogue.value.section_slug}`
})
const firstIllustration = computed(() => dialogue.value?.illustrations?.[0] || null)
const shortIllustrationCaption = computed(() => {
  const words = (firstIllustration.value?.caption || '').trim().split(/\s+/).filter(Boolean)
  return words.length > 12 ? `${words.slice(0, 12).join(' ')}…` : words.join(' ')
})
const illustrationCaptionTruncated = computed(() => {
  return (firstIllustration.value?.caption || '').trim().split(/\s+/).filter(Boolean).length > 12
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
  illustrationCaptionExpanded.value = false
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

function openResource(type) {
  resourceModal.value = { open: true, type }
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

async function archiveDialogue() {
  if (!canArchive.value) return
  dialogueActionError.value = ''
  archiving.value = true
  try {
    await api.post(`/dialogues/${route.params.id}/moderate/`, { status: 'archived' })
    router.push({ name: 'archive' })
  } catch {
    dialogueActionError.value = t('dialogue.deleteError')
  } finally {
    archiving.value = false
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

.dialogue-status {
  border-radius: 999px;
  font-size: 0.72rem;
  font-weight: 600;
  padding: 0.1rem 0.5rem;
}
.dialogue-status.published { background: #dcfce7; color: #166534; }
.dialogue-status.submitted { background: #dbeafe; color: #1d4ed8; }
.dialogue-status.changes_requested { background: #fef9c3; color: #854d0e; }
.dialogue-status.rejected { background: #fee2e2; color: #991b1b; }
.dialogue-status.archived { background: #ede9fe; color: #5b21b6; }

.author-profile {
  color: var(--color-text-muted);
  font-size: 0.82rem;
  margin-top: 0.35rem;
}

.dialogue-resource-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin: -0.5rem 0 1.5rem;
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

.dialogue-access {
  margin: 1.5rem 0;
}

.dialogue-access h2 {
  color: var(--color-primary);
  font-family: var(--font-serif);
  font-size: 1.125rem;
  margin-bottom: 1rem;
}

.dialogue-access-options {
  display: grid;
  gap: 1rem;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
}

.dialogue-access-option {
  align-items: flex-start;
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  display: flex;
  flex-direction: column;
  gap: 0.9rem;
  justify-content: space-between;
  padding: 1rem;
}

.dialogue-access-option p {
  color: var(--color-text-muted);
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

.illustrations-menu.single-illustration { display: block; }

.text-toggle {
  background: none;
  border: 0;
  color: var(--color-primary);
  cursor: pointer;
  font: inherit;
  margin-left: 0.35rem;
  text-decoration: underline;
}

.literature-item {
  border-bottom: 1px solid var(--color-border);
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
  padding: 0.65rem 0;
}

.literature-item span,
.literature-item p { color: var(--color-text-muted); }

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
