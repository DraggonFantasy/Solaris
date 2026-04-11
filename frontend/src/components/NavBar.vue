<template>
  <nav class="navbar">
    <div class="navbar-inner">
      <RouterLink class="navbar-brand" to="/">
        <span class="brand-text">СОЛЯРИС</span>
      </RouterLink>

      <div class="navbar-links">
        <RouterLink to="/sections">{{ t('nav.sections') }}</RouterLink>
        <RouterLink to="/dialogues" v-if="false">{{ t('nav.dialogues') }}</RouterLink>
      </div>

      <div class="navbar-right">
        <LanguageSwitcher />

        <template v-if="auth.isAuthenticated">
          <RouterLink to="/my-dialogues">{{ t('dialogue.myDialogues') }}</RouterLink>
          <RouterLink class="btn btn-primary btn-sm" to="/dialogues/create">+ {{ t('dialogue.createBtn') }}</RouterLink>
          <RouterLink class="navbar-user" to="/profile">{{ auth.user?.username }}</RouterLink>
          <a v-if="auth.isStaff" href="/admin/" class="btn btn-outline btn-sm">
            {{ t('nav.admin') }}
          </a>
          <button class="btn btn-outline btn-sm" @click="handleLogout">
            {{ t('nav.logout') }}
          </button>
        </template>
        <template v-else>
          <RouterLink class="btn btn-outline btn-sm" to="/login">{{ t('nav.login') }}</RouterLink>
          <RouterLink class="btn btn-primary btn-sm" to="/register">{{ t('nav.register') }}</RouterLink>
        </template>
      </div>
    </div>
  </nav>
</template>

<script setup>
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import LanguageSwitcher from './LanguageSwitcher.vue'

const { t } = useI18n()
const auth = useAuthStore()
const router = useRouter()

async function handleLogout() {
  await auth.logout()
  router.push('/')
}
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
  font-family: var(--font-serif);
  font-size: 1.25rem;
  font-weight: 700;
  color: var(--color-primary);
  letter-spacing: 0.1em;
}

.navbar-links {
  display: flex;
  gap: 1.5rem;
  flex: 1;
}

.navbar-links a {
  color: var(--color-text-muted);
  text-decoration: none;
  font-size: 0.9375rem;
  font-weight: 500;
  transition: color 0.15s;
}

.navbar-links a:hover,
.navbar-links a.router-link-active {
  color: var(--color-primary);
}

.navbar-right {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.navbar-user {
  font-weight: 500;
  color: var(--color-text);
  text-decoration: none;
  font-size: 0.9375rem;
}

.navbar-user:hover {
  color: var(--color-primary);
}

.btn-sm {
  padding: 0.375rem 0.875rem;
  font-size: 0.875rem;
}
</style>
