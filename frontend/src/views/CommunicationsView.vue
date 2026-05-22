<template>
  <div>
    <h1 class="page-title">{{ t('communications.title') }}</h1>
    <p class="page-intro">{{ t('communications.intro') }}</p>

    <div class="communication-grid">
      <RouterLink v-if="auth.isAuthenticated" class="communication-card card" to="/my-dialogues">
        <h2>{{ t('dialogue.myDialogues') }}</h2>
        <p>{{ t('communications.myDialoguesText') }}</p>
      </RouterLink>

      <RouterLink v-if="auth.isAuthenticated" class="communication-card card" to="/dialogues/create">
        <h2>{{ t('dialogue.createBtn') }}</h2>
        <p>{{ t('communications.createDialogueText') }}</p>
      </RouterLink>

      <RouterLink v-if="auth.isStaff" class="communication-card card" to="/moderation/dialogues">
        <h2>{{ t('nav.review') }}</h2>
        <p>{{ t('communications.reviewText') }}</p>
      </RouterLink>

      <RouterLink v-if="auth.isStaff" class="communication-card card" to="/moderation/comments">
        <h2>{{ t('nav.commentReview') }}</h2>
        <p>{{ t('communications.commentsText') }}</p>
      </RouterLink>

      <a v-if="auth.isStaff" class="communication-card card" href="/admin/">
        <h2>{{ t('nav.admin') }}</h2>
        <p>{{ t('communications.adminText') }}</p>
      </a>

      <RouterLink v-if="!auth.isAuthenticated" class="communication-card card" to="/login">
        <h2>{{ t('auth.loginTitle') }}</h2>
        <p>{{ t('communications.loginText') }}</p>
      </RouterLink>
    </div>
  </div>
</template>

<script setup>
import { useI18n } from 'vue-i18n'
import { useAuthStore } from '../stores/auth'

const { t } = useI18n()
const auth = useAuthStore()
</script>

<style scoped>
.page-intro {
  color: var(--color-text-muted);
  line-height: 1.7;
  margin: -0.75rem 0 1.5rem;
  max-width: 680px;
}

.communication-grid {
  display: grid;
  gap: 1rem;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
}

.communication-card {
  color: inherit;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  min-height: 150px;
  text-decoration: none;
  transition: box-shadow 0.2s, transform 0.2s;
}

.communication-card:hover {
  box-shadow: var(--shadow-md);
  transform: translateY(-2px);
}

.communication-card h2 {
  color: var(--color-primary);
  font-family: var(--font-serif);
  font-size: 1.05rem;
}

.communication-card p {
  color: var(--color-text-muted);
  font-size: 0.9rem;
  line-height: 1.6;
}
</style>
