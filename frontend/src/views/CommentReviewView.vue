<template>
  <div>
    <div class="page-header">
      <h1 class="page-title">{{ t('commentModeration.title') }}</h1>
      <select v-model="approvedFilter" class="status-filter" @change="loadComments">
        <option value="false">{{ t('commentModeration.pending') }}</option>
        <option value="true">{{ t('commentModeration.approved') }}</option>
        <option value="all">{{ t('commentModeration.all') }}</option>
      </select>
    </div>

    <div v-if="!auth.isStaff" class="alert alert-error">{{ t('commentModeration.staffOnly') }}</div>
    <div v-else-if="loading" class="text-muted">{{ t('common.loading') }}</div>
    <div v-else-if="comments.length === 0" class="empty-state card">{{ t('commentModeration.empty') }}</div>

    <div v-else class="comment-review-list">
      <article v-for="comment in comments" :key="comment.id" class="comment-review-row card">
        <div class="comment-review-main">
          <RouterLink :to="`/dialogues/${comment.dialogue_id}`" class="dialogue-link">
            {{ comment.dialogue_title }}
          </RouterLink>
          <div class="comment-meta">
            <span>{{ comment.author_username }}</span>
            <span>{{ formatDate(comment.created_at) }}</span>
            <span class="comment-status" :class="{ approved: comment.approved }">
              {{ comment.approved ? t('commentModeration.approved') : t('commentModeration.pending') }}
            </span>
          </div>
          <div v-if="comment.parent" class="parent-comment">
            <strong>{{ t('commentModeration.replyTo') }} {{ comment.parent_author_username }}</strong>
            <p>{{ comment.parent_text }}</p>
          </div>
          <p class="comment-text">{{ comment.text }}</p>
        </div>

        <div class="comment-actions">
          <button
            v-if="!comment.approved"
            class="btn btn-primary btn-sm"
            type="button"
            :disabled="savingId === comment.id"
            @click="moderate(comment, 'approve')"
          >
            {{ t('commentModeration.approve') }}
          </button>
          <button
            class="btn btn-outline btn-sm"
            type="button"
            :disabled="savingId === comment.id"
            @click="moderate(comment, 'reject')"
          >
            {{ t('commentModeration.reject') }}
          </button>
        </div>
      </article>
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
const comments = ref([])
const loading = ref(true)
const savingId = ref(null)
const approvedFilter = ref('false')

onMounted(loadComments)

async function loadComments() {
  if (!auth.isStaff) {
    loading.value = false
    return
  }
  loading.value = true
  try {
    const { data } = await api.get('/comments/review/', {
      params: { approved: approvedFilter.value },
    })
    comments.value = data.results || data
  } finally {
    loading.value = false
  }
}

async function moderate(comment, action) {
  savingId.value = comment.id
  try {
    const { data } = await api.post(`/comments/${comment.id}/moderate/`, { action })
    if (action === 'approve') {
      comment.approved = data.approved
      if (approvedFilter.value === 'false') {
        comments.value = comments.value.filter((item) => item.id !== comment.id)
      }
    } else {
      comments.value = comments.value.filter((item) => item.id !== comment.id)
    }
  } finally {
    savingId.value = null
  }
}

function formatDate(iso) {
  return new Date(iso).toLocaleDateString()
}
</script>

<style scoped>
.page-header {
  align-items: center;
  display: flex;
  gap: 1rem;
  justify-content: space-between;
  margin-bottom: 1.5rem;
}

.page-header .page-title {
  margin-bottom: 0;
}

.status-filter {
  min-width: 220px;
}

.empty-state {
  color: var(--color-text-muted);
  padding: 2rem;
}

.comment-review-list {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.comment-review-row {
  display: grid;
  gap: 1.25rem;
  grid-template-columns: minmax(0, 1fr) 180px;
}

.dialogue-link {
  color: var(--color-text);
  font-family: var(--font-serif);
  font-weight: 700;
  text-decoration: none;
}

.dialogue-link:hover {
  color: var(--color-primary);
}

.comment-meta {
  align-items: center;
  color: var(--color-text-muted);
  display: flex;
  flex-wrap: wrap;
  font-size: 0.8rem;
  gap: 0.75rem;
  margin-top: 0.5rem;
}

.comment-status {
  background: #fef3c7;
  border-radius: 999px;
  color: #92400e;
  font-size: 0.7rem;
  font-weight: 600;
  padding: 0.1rem 0.45rem;
}

.comment-status.approved {
  background: #dcfce7;
  color: #166534;
}

.comment-text {
  line-height: 1.55;
  margin-top: 0.75rem;
  white-space: pre-wrap;
}

.parent-comment {
  background: var(--color-bg);
  border-left: 3px solid var(--color-border);
  color: var(--color-text-muted);
  font-size: 0.82rem;
  margin-top: 0.75rem;
  padding: 0.55rem 0.75rem;
}

.parent-comment strong {
  color: var(--color-text);
  display: block;
  margin-bottom: 0.25rem;
}

.parent-comment p {
  display: -webkit-box;
  line-height: 1.45;
  margin: 0;
  overflow: hidden;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.comment-actions {
  align-items: flex-start;
  display: flex;
  flex-direction: column;
  gap: 0.6rem;
}

@media (max-width: 760px) {
  .page-header {
    align-items: stretch;
    flex-direction: column;
  }

  .comment-review-row {
    grid-template-columns: 1fr;
  }

  .comment-actions {
    flex-direction: row;
  }
}
</style>
