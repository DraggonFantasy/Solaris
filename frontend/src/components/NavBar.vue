<template>
  <nav class="navbar">
    <div class="navbar-inner">
      <div class="navbar-links">
        <RouterLink to="/sections">{{ t('nav.sections') }}</RouterLink>
      </div>

      <div class="navbar-right">
        <LanguageSwitcher />
        <RouterLink to="/communications">{{ t('nav.communications') }}</RouterLink>
      </div>
    </div>
  </nav>
</template>

<script setup>
import { useI18n } from 'vue-i18n'
import LanguageSwitcher from './LanguageSwitcher.vue'

const { t } = useI18n()
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

.navbar-links {
  display: flex;
  gap: 1.5rem;
  flex: 1;
}

.navbar-links a,
.navbar-right a {
  color: var(--color-text-muted);
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

.navbar-right {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}
</style>
