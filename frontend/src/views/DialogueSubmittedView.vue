<template>
  <div class="submitted-page">
    <div class="submitted-card card">
      <div class="icon">✓</div>
      <h1>{{ t('dialogue.submittedTitle') }}</h1>
      <p>{{ t('dialogue.submittedText') }}</p>
      <div class="actions">
        <RouterLink class="btn btn-primary" to="/">{{ t('nav.home') }}</RouterLink>
        <RouterLink class="btn btn-outline" to="/my-dialogues">{{ t('dialogue.myDialogues') }}</RouterLink>
      </div>
    </div>
  </div>
</template>

<script setup>
import { useI18n } from 'vue-i18n'
const { t } = useI18n()
</script>

<style scoped>
.submitted-page {
  display: flex;
  justify-content: center;
  padding-top: 4rem;
}

.submitted-card {
  max-width: 480px;
  width: 100%;
  text-align: center;
  padding: 3rem 2rem;
}

.icon {
  width: 64px;
  height: 64px;
  background: var(--color-success);
  color: white;
  border-radius: 50%;
  font-size: 1.75rem;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 1.5rem;
}

h1 {
  font-family: var(--font-serif);
  font-size: 1.5rem;
  margin-bottom: 0.75rem;
}

p {
  color: var(--color-text-muted);
  margin-bottom: 2rem;
  line-height: 1.7;
}

.actions {
  display: flex;
  gap: 1rem;
  justify-content: center;
}
</style>
