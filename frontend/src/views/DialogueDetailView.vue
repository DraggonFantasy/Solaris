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
        <div v-for="c in dialogue.comments" :key="c.id" class="comment card" :class="{ pending: !c.approved }">
          <div class="comment-meta">
            <strong>{{ c.author_username }}</strong>
            <span>{{ formatDate(c.created_at) }}</span>
            <span v-if="!c.approved" class="pending-badge">{{ t('dialogues.pendingComment') }}</span>
          </div>
          <p>{{ c.text }}</p>
        </div>
      </div>

      <form v-if="auth.isAuthenticated" class="comment-form" @submit.prevent="submitComment">
        <div v-if="commentNotice" class="alert alert-success">{{ commentNotice }}</div>
        <div v-if="commentError" class="alert alert-error">{{ commentError }}</div>
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
const commentText = ref('')
const commentNotice = ref('')
const commentError = ref('')
const submittingComment = ref(false)
const withdrawing = ref(false)

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

onMounted(async () => {
  try {
    const { data } = await api.get(`/dialogues/${route.params.id}/`)
    dialogue.value = data
  } finally {
    loading.value = false
  }
})

function formatDate(iso) {
  return new Date(iso).toLocaleDateString()
}

async function toggleLike() {
  if (!auth.isAuthenticated || !isPublished.value) return
  const { data } = await api.post(`/dialogues/${route.params.id}/like/`)
  dialogue.value.user_has_liked = data.liked
  dialogue.value.likes_count = data.likes_count
}

async function submitComment() {
  if (!commentText.value.trim() || !isPublished.value) return
  commentNotice.value = ''
  commentError.value = ''
  submittingComment.value = true
  try {
    await api.post(`/dialogues/${route.params.id}/comments/`, { text: commentText.value })
    commentText.value = ''
    commentNotice.value = t('dialogues.commentPendingNotice')
    const { data } = await api.get(`/dialogues/${route.params.id}/`)
    dialogue.value = data
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
    dialogue.value = data
  } finally {
    withdrawing.value = false
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
