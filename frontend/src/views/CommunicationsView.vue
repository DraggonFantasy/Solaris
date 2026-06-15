<template>
  <div>
    <h1 class="page-title">{{ t('communications.title') }}</h1>
    <p class="page-intro">{{ t('communications.intro') }}</p>

    <div v-if="!auth.isStaff" class="alert alert-error">{{ t('moderation.staffOnly') }}</div>
    <div v-else-if="loading" class="text-muted">{{ t('common.loading') }}</div>
    <div v-else>
      <div v-if="error" class="alert alert-error">{{ error }}</div>

      <section class="queue-section">
        <header class="queue-header">
          <h2>{{ t('communications.dialogueRequests') }}</h2>
          <span>{{ t('communications.requestCount', { count: pendingDialogues.length }) }}</span>
        </header>

        <div v-if="pendingDialogues.length === 0" class="empty-state card">
          {{ t('communications.emptyDialogues') }}
        </div>
        <div v-else class="request-list">
          <article v-for="dialogue in pendingDialogues" :key="dialogue.id" class="request-row card">
            <div class="request-main">
              <div class="dialogue-section-tag">{{ dialogue.section_name }}</div>
              <RouterLink :to="`/dialogues/${dialogue.id}`" class="request-title">
                {{ dialogue.title }}
              </RouterLink>
              <p v-if="dialogue.summary" class="request-summary">{{ dialogue.summary }}</p>
              <div class="request-meta">
                <span>{{ dialogue.human_author_username || t('moderation.unknownAuthor') }}</span>
                <span>{{ formatDate(dialogue.created_at) }}</span>
              </div>
              <div v-if="dialogue.review_note" class="request-note">
                <strong>{{ t('dialogue.reviewNote') }}</strong>
                <p>{{ dialogue.review_note }}</p>
              </div>
            </div>

            <div class="request-actions">
              <RouterLink class="btn btn-outline btn-sm" :to="{ name: 'edit-dialogue', params: { id: dialogue.id } }">
                {{ t('dialogue.edit') }}
              </RouterLink>
              <button
                class="btn btn-primary btn-sm"
                type="button"
                :disabled="savingKey === `dialogue-${dialogue.id}`"
                @click="moderateDialogue(dialogue, 'published')"
              >
                {{ t('moderation.publish') }}
              </button>
              <button
                class="btn btn-outline btn-sm"
                type="button"
                :disabled="savingKey === `dialogue-${dialogue.id}`"
                @click="openChangesModal(dialogue)"
              >
                {{ t('moderation.requestChanges') }}
              </button>
              <button
                class="btn btn-danger btn-sm"
                type="button"
                :disabled="savingKey === `dialogue-${dialogue.id}`"
                @click="moderateDialogue(dialogue, 'rejected')"
              >
                {{ t('moderation.reject') }}
              </button>
            </div>
          </article>
        </div>
      </section>

      <section class="queue-section">
        <header class="queue-header">
          <h2>{{ t('communications.commentRequests') }}</h2>
          <span>{{ t('communications.requestCount', { count: pendingComments.length }) }}</span>
        </header>

        <div v-if="pendingComments.length === 0" class="empty-state card">
          {{ t('communications.emptyComments') }}
        </div>
        <div v-else class="request-list">
          <article v-for="comment in pendingComments" :key="comment.id" class="request-row card">
            <div class="request-main">
              <RouterLink :to="`/dialogues/${comment.dialogue_id}`" class="request-title">
                {{ comment.dialogue_title }}
              </RouterLink>
              <div class="request-meta">
                <span>{{ comment.author_username }}</span>
                <span>{{ formatDate(comment.created_at) }}</span>
              </div>
              <div v-if="comment.parent" class="request-note">
                <strong>{{ t('commentModeration.replyTo') }} {{ comment.parent_author_username }}</strong>
                <p>{{ comment.parent_text }}</p>
              </div>
              <p class="comment-text">{{ comment.text }}</p>
            </div>

            <div class="request-actions">
              <button
                class="btn btn-primary btn-sm"
                type="button"
                :disabled="savingKey === `comment-${comment.id}`"
                @click="moderateComment(comment, 'approve')"
              >
                {{ t('commentModeration.approve') }}
              </button>
              <button
                class="btn btn-danger btn-sm"
                type="button"
                :disabled="savingKey === `comment-${comment.id}`"
                @click="moderateComment(comment, 'reject')"
              >
                {{ t('commentModeration.reject') }}
              </button>
            </div>
          </article>
        </div>
      </section>
    </div>

    <div
      v-if="changesDialogue"
      class="changes-modal"
      role="dialog"
      aria-modal="true"
      @click.self="closeChangesModal"
    >
      <form class="changes-modal-content card" @submit.prevent="submitChangesRequest">
        <header class="changes-modal-header">
          <div>
            <h2>{{ t('moderation.requestChanges') }}</h2>
            <p>{{ changesDialogue.title }}</p>
          </div>
          <button type="button" class="changes-modal-close" :aria-label="t('common.close')" @click="closeChangesModal">
            ×
          </button>
        </header>

        <div v-if="error" class="alert alert-error">{{ error }}</div>

        <label class="changes-note-field">
          <span>{{ t('moderation.changesNoteLabel') }}</span>
          <textarea
            v-model="changesNote"
            rows="5"
            :placeholder="t('moderation.changesNotePlaceholder')"
            autofocus
          />
        </label>

        <footer class="changes-modal-actions">
          <button type="button" class="btn btn-outline" @click="closeChangesModal">
            {{ t('common.cancel') }}
          </button>
          <button class="btn btn-primary" type="submit" :disabled="savingKey === `dialogue-${changesDialogue.id}`">
            {{ savingKey === `dialogue-${changesDialogue.id}` ? t('common.loading') : t('moderation.requestChanges') }}
          </button>
        </footer>
      </form>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useAuthStore } from '../stores/auth'
import api from '../api'

const { t } = useI18n()
const auth = useAuthStore()
const pendingDialogues = ref([])
const pendingComments = ref([])
const loading = ref(true)
const savingKey = ref('')
const error = ref('')
const changesDialogue = ref(null)
const changesNote = ref('')

onMounted(async () => {
  if (auth.isAuthenticated && !auth.user) {
    await auth.fetchMe()
  }
  if (!auth.isStaff) {
    loading.value = false
    return
  }
  await loadQueues()
})

async function loadQueues() {
  loading.value = true
  error.value = ''
  try {
    const [dialogueRes, commentRes] = await Promise.all([
      api.get('/dialogues/review/', { params: { status: 'submitted' } }),
      api.get('/comments/review/', { params: { approved: 'false' } }),
    ])
    pendingDialogues.value = (dialogueRes.data.results || dialogueRes.data).map((dialogue) => ({
      ...dialogue,
      moderation_note: dialogue.moderation_note || '',
    }))
    pendingComments.value = commentRes.data.results || commentRes.data
  } catch {
    error.value = t('common.error')
  } finally {
    loading.value = false
  }
}

function openChangesModal(dialogue) {
  error.value = ''
  changesDialogue.value = dialogue
  changesNote.value = dialogue.moderation_note || ''
}

function closeChangesModal() {
  if (savingKey.value) return
  changesDialogue.value = null
  changesNote.value = ''
}

async function submitChangesRequest() {
  if (!changesDialogue.value) return
  const dialogue = changesDialogue.value
  const saved = await moderateDialogue(dialogue, 'changes_requested', changesNote.value)
  if (saved) {
    changesDialogue.value = null
    changesNote.value = ''
  }
}

async function moderateDialogue(dialogue, nextStatus, moderationNote = dialogue.moderation_note || '') {
  savingKey.value = `dialogue-${dialogue.id}`
  error.value = ''
  try {
    await api.post(`/dialogues/${dialogue.id}/moderate/`, {
      status: nextStatus,
      moderation_note: moderationNote,
    })
    pendingDialogues.value = pendingDialogues.value.filter((item) => item.id !== dialogue.id)
    return true
  } catch {
    error.value = t('common.error')
    return false
  } finally {
    savingKey.value = ''
  }
}

async function moderateComment(comment, action) {
  savingKey.value = `comment-${comment.id}`
  error.value = ''
  try {
    await api.post(`/comments/${comment.id}/moderate/`, { action })
    pendingComments.value = pendingComments.value.filter((item) => item.id !== comment.id)
  } catch {
    error.value = t('common.error')
  } finally {
    savingKey.value = ''
  }
}

function formatDate(iso) {
  return new Date(iso).toLocaleDateString()
}
</script>

<style scoped>
.page-intro {
  color: var(--color-text-muted);
  line-height: 1.7;
  margin: -0.75rem 0 1.5rem;
  max-width: 760px;
}

.queue-section {
  margin-top: 2rem;
}

.queue-header {
  align-items: center;
  display: flex;
  gap: 1rem;
  justify-content: space-between;
  margin-bottom: 0.9rem;
}

.queue-header h2 {
  color: var(--color-primary);
  font-family: var(--font-serif);
  font-size: 1.2rem;
  margin: 0;
}

.queue-header span {
  color: var(--color-text-muted);
  font-size: 0.82rem;
  font-weight: 600;
}

.empty-state {
  color: var(--color-text-muted);
  padding: 1.5rem;
}

.request-list {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.request-row {
  display: grid;
  gap: 1.25rem;
  grid-template-columns: minmax(0, 1fr) 180px;
}

.request-main {
  min-width: 0;
}

.dialogue-section-tag {
  color: var(--color-accent);
  font-size: 0.7rem;
  font-weight: 600;
  letter-spacing: 0.05em;
  margin-bottom: 0.35rem;
  text-transform: uppercase;
}

.request-title {
  color: var(--color-text);
  font-family: var(--font-serif);
  font-weight: 700;
  text-decoration: none;
}

.request-title:hover {
  color: var(--color-primary);
}

.request-summary,
.comment-text {
  color: var(--color-text-muted);
  font-size: 0.9rem;
  line-height: 1.55;
  margin-top: 0.6rem;
  white-space: pre-wrap;
}

.request-meta {
  color: var(--color-text-muted);
  display: flex;
  flex-wrap: wrap;
  font-size: 0.8rem;
  gap: 0.75rem;
  margin-top: 0.55rem;
}

.request-note {
  background: var(--color-bg);
  border-left: 3px solid var(--color-primary);
  color: var(--color-text-muted);
  font-size: 0.84rem;
  margin-top: 0.75rem;
  padding: 0.6rem 0.75rem;
}

.request-note strong {
  color: var(--color-text);
  display: block;
  margin-bottom: 0.25rem;
}

.request-note p {
  margin: 0;
  white-space: pre-wrap;
}

.request-actions {
  align-items: stretch;
  display: flex;
  flex-direction: column;
  gap: 0.55rem;
}

.btn-sm {
  font-size: 0.82rem;
  justify-content: center;
  padding: 0.375rem 0.75rem;
}

.changes-modal {
  align-items: center;
  background: rgba(17, 24, 39, 0.72);
  display: flex;
  inset: 0;
  justify-content: center;
  padding: 1.5rem;
  position: fixed;
  z-index: 70;
}

.changes-modal-content {
  max-width: 560px;
  padding: 1.5rem;
  width: 100%;
}

.changes-modal-header {
  align-items: flex-start;
  display: flex;
  gap: 1rem;
  justify-content: space-between;
  margin-bottom: 1.25rem;
}

.changes-modal-header h2 {
  color: var(--color-primary);
  font-family: var(--font-serif);
  font-size: 1.2rem;
  margin-bottom: 0.25rem;
}

.changes-modal-header p {
  color: var(--color-text-muted);
  font-size: 0.86rem;
  line-height: 1.45;
}

.changes-modal-close {
  align-items: center;
  background: transparent;
  border: 0;
  color: var(--color-text-muted);
  cursor: pointer;
  display: flex;
  font-size: 1.4rem;
  height: 2rem;
  justify-content: center;
  line-height: 1;
  width: 2rem;
}

.changes-note-field {
  color: var(--color-text);
  display: flex;
  flex-direction: column;
  font-size: 0.85rem;
  font-weight: 600;
  gap: 0.4rem;
}

.changes-note-field textarea {
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  color: var(--color-text);
  font: inherit;
  font-weight: 400;
  padding: 0.65rem 0.75rem;
  resize: vertical;
}

.changes-note-field textarea:focus {
  border-color: var(--color-primary);
  outline: none;
}

.changes-modal-actions {
  display: flex;
  gap: 0.75rem;
  justify-content: flex-end;
  margin-top: 1.25rem;
}

@media (max-width: 760px) {
  .queue-header {
    align-items: flex-start;
    flex-direction: column;
    gap: 0.25rem;
  }

  .request-row {
    grid-template-columns: 1fr;
  }

  .request-actions {
    flex-direction: row;
    flex-wrap: wrap;
  }
}
</style>
