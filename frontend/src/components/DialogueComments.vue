<template>
  <section
    v-if="isPublished"
    :id="anchorId || undefined"
    class="comments-section"
    :class="{ compact }"
  >
    <h2 v-if="showTitle">{{ t('dialogues.comments') }}</h2>

    <div v-if="threadedComments.length" class="comments-list">
      <div
        v-for="comment in threadedComments"
        :key="comment.id"
        class="comment card"
        :class="{ pending: !comment.approved }"
        :style="{ marginLeft: `${Math.min(comment.depth, 3) * 1.25}rem` }"
      >
        <div class="comment-meta">
          <strong>{{ comment.author_username }}</strong>
          <span>{{ formatDate(comment.created_at) }}</span>
          <span v-if="!comment.approved" class="pending-badge">{{ t('dialogues.pendingComment') }}</span>
        </div>
        <div v-if="comment.parent_author_username" class="reply-context">
          {{ t('dialogues.replyTo') }} {{ comment.parent_author_username }}
        </div>
        <p v-if="editingCommentId !== comment.id">{{ comment.text }}</p>
        <form v-else class="comment-form reply-form" @submit.prevent="saveCommentEdit(comment)">
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
        <div v-if="editingCommentId !== comment.id" class="comment-inline-actions">
          <button
            v-if="auth.isAuthenticated && comment.approved"
            class="comment-action-btn"
            type="button"
            @click="startReply(comment)"
          >
            {{ t('dialogues.reply') }}
          </button>
          <button
            v-if="canEditComment(comment)"
            class="comment-action-btn"
            type="button"
            @click="startCommentEdit(comment)"
          >
            {{ t('dialogues.editComment') }}
          </button>
        </div>

        <form
          v-if="activeReplyId === comment.id"
          class="comment-form reply-form"
          @submit.prevent="submitComment(comment.id)"
        >
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
    <p v-else class="text-muted comments-empty">{{ t('dialogues.noComments') }}</p>

    <div v-if="commentNotice" class="alert alert-success">{{ commentNotice }}</div>
    <div v-if="commentError && !activeReplyId && !editingCommentId" class="alert alert-error">{{ commentError }}</div>

    <button
      v-if="auth.isAuthenticated && !showComposer"
      class="btn btn-primary"
      type="button"
      @click="openComposer"
    >
      + {{ t('dialogues.addComment') }}
    </button>
    <form v-else-if="auth.isAuthenticated" class="comment-form" @submit.prevent="submitComment()">
      <div class="form-group">
        <textarea v-model="commentText" rows="3" required :placeholder="t('dialogues.addComment')" />
      </div>
      <div class="reply-actions">
        <button class="btn btn-primary" type="submit" :disabled="submittingComment">
          {{ submittingComment ? t('common.loading') : t('dialogues.submitComment') }}
        </button>
        <button class="btn btn-outline" type="button" @click="closeComposer">
          {{ t('common.cancel') }}
        </button>
      </div>
    </form>
    <RouterLink
      v-else
      class="btn btn-outline"
      :to="{ name: 'login', query: { redirect: route.fullPath } }"
    >
      {{ t('resources.loginToAdd') }}
    </RouterLink>
  </section>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useAuthStore } from '../stores/auth'
import api from '../api'

const props = defineProps({
  dialogue: { type: Object, required: true },
  showTitle: { type: Boolean, default: true },
  anchorId: { type: String, default: '' },
  compact: { type: Boolean, default: false },
})

const emit = defineEmits(['updated'])
const { t } = useI18n()
const route = useRoute()
const auth = useAuthStore()
const commentText = ref('')
const commentNotice = ref('')
const commentError = ref('')
const submittingComment = ref(false)
const activeReplyId = ref(null)
const replyText = ref('')
const editingCommentId = ref(null)
const editCommentText = ref('')
const showComposer = ref(false)

const isPublished = computed(() => props.dialogue?.status === 'published')
const threadedComments = computed(() => {
  const comments = props.dialogue?.comments || []
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

watch(() => props.dialogue?.id, resetForms)

function resetForms() {
  commentText.value = ''
  commentNotice.value = ''
  commentError.value = ''
  activeReplyId.value = null
  replyText.value = ''
  editingCommentId.value = null
  editCommentText.value = ''
  showComposer.value = false
}

function formatDate(iso) {
  return new Date(iso).toLocaleDateString()
}

function openComposer() {
  commentNotice.value = ''
  commentError.value = ''
  showComposer.value = true
}

function closeComposer() {
  showComposer.value = false
  commentText.value = ''
  commentError.value = ''
}

async function refreshDialogue() {
  const { data } = await api.get(`/dialogues/${props.dialogue.id}/`)
  emit('updated', data)
}

async function submitComment(parentId = null) {
  const text = parentId ? replyText.value : commentText.value
  if (!text.trim() || !isPublished.value) return
  commentNotice.value = ''
  commentError.value = ''
  submittingComment.value = true
  try {
    await api.post(`/dialogues/${props.dialogue.id}/comments/`, {
      text,
      parent: parentId,
    })
    if (parentId) {
      cancelReply()
    } else {
      commentText.value = ''
      showComposer.value = false
    }
    commentNotice.value = t('dialogues.commentPendingNotice')
    await refreshDialogue()
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
    cancelCommentEdit()
    await refreshDialogue()
  } catch {
    commentError.value = t('dialogues.commentSubmitError')
  } finally {
    submittingComment.value = false
  }
}
</script>

<style scoped>
.comments-section {
  margin-top: 2.5rem;
}

.comments-section.compact {
  margin-top: 0;
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

.comments-empty {
  margin-bottom: 1.25rem;
}

.comment {
  font-size: 0.9rem;
}

.comment.pending {
  border-left: 3px solid #f59e0b;
}

.comment-meta {
  align-items: center;
  color: var(--color-text-muted);
  display: flex;
  flex-wrap: wrap;
  font-size: 0.8125rem;
  gap: 1rem;
  margin-bottom: 0.5rem;
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
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  font-family: var(--font-sans);
  font-size: 0.9375rem;
  padding: 0.625rem 0.875rem;
  resize: vertical;
  width: 100%;
}
</style>
