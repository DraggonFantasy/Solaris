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
      </div>
      <div v-else-if="canWithdraw" class="dialogue-actions">
        <button class="btn btn-outline" :disabled="withdrawing" @click="withdrawFromReview">
          {{ withdrawing ? t('common.loading') : t('dialogue.withdrawReview') }}
        </button>
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
          <textarea v-model="moderationNoteDraft" rows="2" :placeholder="t('moderation.notePlaceholder')" />
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

    <div class="dialogue-text card">
      <MarkdownRenderer :content="dialogue.text" />
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

    <!-- Comments -->
    <section v-if="isPublished" id="comments" class="comments-section">
      <h2>{{ t('dialogues.addComment') }}</h2>
      <div class="comments-list">
        <div
          v-for="c in threadedComments"
          :key="c.id"
          class="comment card"
          :class="{ pending: !c.approved }"
          :style="{ marginLeft: `${Math.min(c.depth, 3) * 1.25}rem` }"
        >
          <div class="comment-meta">
            <strong>{{ c.author_username }}</strong>
            <span>{{ formatDate(c.created_at) }}</span>
            <span v-if="!c.approved" class="pending-badge">{{ t('dialogues.pendingComment') }}</span>
          </div>
          <div v-if="c.parent_author_username" class="reply-context">
            {{ t('dialogues.replyTo') }} {{ c.parent_author_username }}
          </div>
          <p v-if="editingCommentId !== c.id">{{ c.text }}</p>
          <form v-else class="comment-form reply-form" @submit.prevent="saveCommentEdit(c)">
            <div v-if="commentError" class="alert alert-error">{{ commentError }}</div>
            <div class="form-group">
              <textarea v-model="editCommentText" rows="3" required />
            </div>
            <div class="reply-actions">
              <button class="btn btn-primary btn-sm" type="submit" :disabled="submittingComment">
                {{ submittingComment ? t('common.loading') : t('common.save') }}
              </button>
              <button class="btn btn-outline btn-sm" type="button" @click="cancelCommentEdit">
                {{ t('common.cancel') }}
              </button>
            </div>
          </form>
          <div v-if="editingCommentId !== c.id" class="comment-inline-actions">
            <button v-if="auth.isAuthenticated && c.approved" class="comment-action-btn" type="button" @click="startReply(c)">
              {{ t('dialogues.reply') }}
            </button>
            <button v-if="canEditComment(c)" class="comment-action-btn" type="button" @click="startCommentEdit(c)">
              {{ t('dialogues.editComment') }}
            </button>
          </div>

          <form v-if="activeReplyId === c.id" class="comment-form reply-form" @submit.prevent="submitComment(c.id)">
            <div v-if="commentError" class="alert alert-error">{{ commentError }}</div>
            <div class="form-group">
              <textarea v-model="replyText" rows="3" required :placeholder="t('dialogues.replyPlaceholder')" />
            </div>
            <div class="reply-actions">
              <button class="btn btn-primary btn-sm" type="submit" :disabled="submittingComment">
                {{ submittingComment ? t('common.loading') : t('dialogues.submitComment') }}
              </button>
              <button class="btn btn-outline btn-sm" type="button" @click="cancelReply">
                {{ t('common.cancel') }}
              </button>
            </div>
          </form>
        </div>
      </div>

      <form v-if="auth.isAuthenticated" class="comment-form" @submit.prevent="submitComment()">
        <div v-if="commentNotice" class="alert alert-success">{{ commentNotice }}</div>
        <div v-if="commentError && !activeReplyId" class="alert alert-error">{{ commentError }}</div>
        <div class="form-group">
          <textarea v-model="commentText" rows="3" required :placeholder="t('dialogues.addComment')" />
        </div>
        <button class="btn btn-primary" type="submit" :disabled="submittingComment">
          {{ submittingComment ? t('common.loading') : t('dialogues.submitComment') }}
        </button>
      </form>
    </section>

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
import { useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useAuthStore } from '../stores/auth'
import api from '../api'
import MarkdownRenderer from '../components/MarkdownRenderer.vue'

const { t } = useI18n()
const route = useRoute()
const auth = useAuthStore()
const dialogue = ref(null)
const loading = ref(true)
const detailErrorStatus = ref(null)
const commentText = ref('')
const commentNotice = ref('')
const commentError = ref('')
const submittingComment = ref(false)
const activeReplyId = ref(null)
const replyText = ref('')
const editingCommentId = ref(null)
const editCommentText = ref('')
const withdrawing = ref(false)
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
const threadedComments = computed(() => {
  const comments = dialogue.value?.comments || []
  const byParent = new Map()
  const ids = new Set(comments.map((comment) => comment.id))
  comments.forEach((comment) => {
    const parentId = comment.parent && ids.has(comment.parent) ? comment.parent : null
    if (!byParent.has(parentId)) byParent.set(parentId, [])
    byParent.get(parentId).push(comment)
  })

  const flatten = (parentId = null, depth = 0, seen = new Set()) => {
    return (byParent.get(parentId) || []).flatMap((comment) => {
      if (seen.has(comment.id)) return []
      const nextSeen = new Set(seen)
      nextSeen.add(comment.id)
      return [
        { ...comment, depth },
        ...flatten(comment.id, depth + 1, nextSeen),
      ]
    })
  }

  return flatten()
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

async function submitComment(parentId = null) {
  const text = parentId ? replyText.value : commentText.value
  if (!text.trim() || !isPublished.value) return
  commentNotice.value = ''
  commentError.value = ''
  submittingComment.value = true
  try {
    await api.post(`/dialogues/${route.params.id}/comments/`, {
      text,
      parent: parentId,
    })
    if (parentId) {
      cancelReply()
    } else {
      commentText.value = ''
    }
    commentNotice.value = t('dialogues.commentPendingNotice')
    const { data } = await api.get(`/dialogues/${route.params.id}/`)
    setDialogue(data)
  } catch {
    commentError.value = t('dialogues.commentSubmitError')
  } finally {
    submittingComment.value = false
  }
}

function canEditComment(comment) {
  return auth.isAuthenticated && !comment.approved && comment.author_id === auth.user?.id
}

function startReply(comment) {
  if (!comment.approved) return
  activeReplyId.value = comment.id
  editingCommentId.value = null
  editCommentText.value = ''
  replyText.value = ''
  commentError.value = ''
}

function cancelReply() {
  activeReplyId.value = null
  replyText.value = ''
}

function startCommentEdit(comment) {
  editingCommentId.value = comment.id
  activeReplyId.value = null
  replyText.value = ''
  editCommentText.value = comment.text
  commentError.value = ''
}

function cancelCommentEdit() {
  editingCommentId.value = null
  editCommentText.value = ''
}

async function saveCommentEdit(comment) {
  if (!editCommentText.value.trim()) return
  commentError.value = ''
  submittingComment.value = true
  try {
    await api.patch(`/comments/${comment.id}/`, { text: editCommentText.value })
    comment.text = editCommentText.value
    cancelCommentEdit()
  } catch {
    commentError.value = t('dialogues.commentSubmitError')
  } finally {
    submittingComment.value = false
  }
}

async function withdrawFromReview() {
  if (!canWithdraw.value) return
  withdrawing.value = true
  try {
    const { data } = await api.post(`/dialogues/${route.params.id}/withdraw/`)
    setDialogue(data)
  } finally {
    withdrawing.value = false
  }
}

async function updateDialogueStatus() {
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
  z-index: 50;
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

.comments-section {
  margin-top: 2.5rem;
}

.comments-section h2 {
  font-family: var(--font-serif);
  font-size: 1.25rem;
  margin-bottom: 1.25rem;
}

.comments-list {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  margin-bottom: 1.5rem;
}

.comment {
  font-size: 0.9rem;
}

.comment.pending {
  border-left: 3px solid #f59e0b;
}

.comment-meta {
  align-items: center;
  display: flex;
  flex-wrap: wrap;
  gap: 1rem;
  margin-bottom: 0.5rem;
  font-size: 0.8125rem;
  color: var(--color-text-muted);
}

.pending-badge {
  background: #fef3c7;
  border-radius: 999px;
  color: #92400e;
  font-size: 0.7rem;
  font-weight: 600;
  padding: 0.1rem 0.45rem;
}

.reply-context {
  color: var(--color-text-muted);
  font-size: 0.78rem;
  margin-bottom: 0.4rem;
}

.comment-inline-actions {
  display: flex;
  gap: 0.75rem;
  margin-top: 0.75rem;
}

.comment-action-btn {
  background: transparent;
  border: 0;
  color: var(--color-primary);
  cursor: pointer;
  font-size: 0.82rem;
  padding: 0;
}

.comment-action-btn:hover {
  text-decoration: underline;
}

.reply-form {
  border-top: 1px solid var(--color-border);
  margin-top: 0.75rem;
  padding-top: 0.75rem;
}

.reply-actions {
  display: flex;
  gap: 0.5rem;
}

.comment-form textarea {
  width: 100%;
  padding: 0.625rem 0.875rem;
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  font-family: var(--font-sans);
  font-size: 0.9375rem;
  resize: vertical;
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
