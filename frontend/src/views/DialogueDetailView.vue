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

    <div v-if="dialogue.illustrations?.length" class="dialogue-block">
      <h2>{{ t('dialogues.illustrations') }}</h2>
      <div class="illustrations">
        <figure v-for="ill in dialogue.illustrations" :key="ill.id">
          <img :src="ill.image" :alt="ill.caption" />
          <figcaption>{{ ill.caption }}</figcaption>
        </figure>
      </div>
    </div>

    <!-- Like button -->
    <div v-if="isPublished" class="like-row">
      <button class="btn" :class="dialogue.user_has_liked ? 'btn-primary' : 'btn-outline'" @click="toggleLike">
        ♥ {{ dialogue.likes_count }}
      </button>
    </div>

    <!-- Comments -->
    <section v-if="isPublished" class="comments-section">
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
}

function formatDate(iso) {
  return new Date(iso).toLocaleDateString()
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

.illustrations {
  display: flex;
  flex-wrap: wrap;
  gap: 1rem;
}

.illustrations figure {
  max-width: 400px;
}

.illustrations img {
  width: 100%;
  border-radius: var(--radius);
}

.illustrations figcaption {
  font-size: 0.8125rem;
  color: var(--color-text-muted);
  margin-top: 0.5rem;
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
</style>
