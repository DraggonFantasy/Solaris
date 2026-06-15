<template>
  <nav class="navbar">
    <div class="navbar-inner">
      <RouterLink class="navbar-brand" to="/">
        <span class="brand-text">СОЛЯРИС</span>
      </RouterLink>

      <div class="navbar-links">
        <RouterLink to="/sections">{{ t('nav.sections') }}</RouterLink>
      </div>

      <div class="navbar-right">
        <LanguageSwitcher />
        <RouterLink v-if="auth.isStaff" to="/communications">
          {{ t('nav.communications') }}
        </RouterLink>
        <button v-else type="button" class="navbar-static-button" disabled>
          {{ t('nav.communications') }}
        </button>
      </div>
    </div>
  </nav>
</template>

<script setup>
import { useI18n } from 'vue-i18n'
import { useAuthStore } from '../stores/auth'
import LanguageSwitcher from './LanguageSwitcher.vue'

const { t } = useI18n()
const auth = useAuthStore()
</script>

<style scoped>
.navbar {
  background: var(--color-surface);
  border-bottom: 1px solid var(--color-border);
  position: sticky;
  top: 0;
  z-index: 100;
  box-shadow: var(--shadow);
}

.navbar-inner {
  max-width: 1100px;
  margin: 0 auto;
  padding: 0 1.5rem;
  height: 60px;
  display: flex;
  align-items: center;
  gap: 2rem;
}

.navbar-brand {
  text-decoration: none;
}

.brand-text {
  color: var(--color-primary);
  font-family: var(--font-serif);
  font-size: 1.25rem;
  font-weight: 700;
  letter-spacing: 0.1em;
}

.navbar-links {
  display: flex;
  gap: 1.5rem;
  flex: 1;
}

.navbar-links a,
.navbar-right a,
.navbar-static-button {
  color: var(--color-text-muted);
  background: transparent;
  border: 0;
  cursor: default;
  font-family: var(--font-sans);
  text-decoration: none;
  font-size: 0.9375rem;
  font-weight: 500;
  transition: color 0.15s;
}

.navbar-links a:hover,
.navbar-links a.router-link-active,
.navbar-right a:hover,
.navbar-right a.router-link-active {
  color: var(--color-primary);
}

.navbar-static-button:disabled {
  opacity: 1;
}

.navbar-right {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}
</style>
