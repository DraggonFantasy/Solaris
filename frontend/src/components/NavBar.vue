<template>
  <nav class="navbar">
    <div class="navbar-inner">
      <RouterLink class="navbar-brand nav-button" to="/">
        <span class="brand-text">Соляріс</span>
      </RouterLink>

      <div class="navbar-links">
        <RouterLink class="nav-button" to="/sections">{{ t('nav.sections') }}</RouterLink>
      </div>

      <div class="navbar-right">
        <RouterLink v-if="auth.isAuthenticated" class="nav-button" to="/communications">
          {{ t('nav.communications') }}
        </RouterLink>
        <button v-else type="button" class="nav-button navbar-static-button" disabled>
          {{ t('nav.communications') }}
        </button>
        <LanguageSwitcher />
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

.navbar-brand:hover .brand-text,
.navbar-brand.router-link-active .brand-text { color: white; }

.navbar-links {
  display: flex;
  gap: 1.5rem;
  flex: 1;
}

.nav-button {
  color: var(--color-primary);
  background: var(--color-surface);
  border: 1px solid var(--color-primary);
  border-radius: var(--radius);
  cursor: default;
  font-family: var(--font-sans);
  text-decoration: none;
  font-size: 0.9375rem;
  font-weight: 500;
  padding: 0.35rem 0.7rem;
  transition: background 0.15s, color 0.15s;
}

.nav-button:hover,
.nav-button.router-link-active {
  background: var(--color-primary);
  color: white;
}

.navbar-static-button:disabled {
  opacity: 0.55;
}

.navbar-right {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}
</style>
