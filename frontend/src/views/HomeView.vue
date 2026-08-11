<template>
  <div class="home">
    <section class="hero">
      <div class="hero-content">
        <img class="hero-logo" src="/logo.png" alt="Солярис" />
        <h1 class="hero-title">СОЛЯРИС</h1>
        <p class="hero-tagline">{{ t('home.tagline') }}</p>
        <p class="hero-brief">{{ t('home.brief') }}</p>
        <div class="hero-actions">
          <button type="button" class="btn btn-primary" @click="showAbout = true">
            {{ t('home.aboutProject') }}
          </button>
          <RouterLink v-if="!auth.isAuthenticated" class="btn btn-outline btn-compact" to="/login">
            {{ t('nav.login') }}
          </RouterLink>
        </div>
      </div>
    </section>

    <Teleport to="body">
      <div v-if="showAbout" class="about-modal" role="dialog" aria-modal="true" @click.self="showAbout = false">
        <div class="about-modal-content card">
          <header class="about-modal-header">
            <h2>{{ t('home.aboutProject') }}</h2>
            <button type="button" class="about-modal-close" :aria-label="t('common.close')" @click="showAbout = false">
              ×
            </button>
          </header>
          <div class="about-modal-body">
            <MarkdownRenderer :content="t('home.aboutText')" />
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useAuthStore } from '../stores/auth'
import MarkdownRenderer from '../components/MarkdownRenderer.vue'

const { t } = useI18n()
const auth = useAuthStore()
const showAbout = ref(false)
</script>

<style scoped>
.hero {
  text-align: center;
  padding: 4rem 1rem 3rem;
  border-bottom: 1px solid var(--color-border);
  margin-bottom: 3rem;
}

.hero-title {
  font-family: var(--font-serif);
  font-size: 3.5rem;
  font-weight: 700;
  color: var(--color-primary);
  letter-spacing: 0.15em;
  margin-bottom: 1rem;
}

.hero-logo {
  display: block;
  height: auto;
  margin: 0 auto 1.5rem;
  max-width: min(360px, 72vw);
}

.hero-tagline {
  font-size: 1.25rem;
  color: var(--color-text-muted);
  margin-bottom: 1.5rem;
  font-style: italic;
}

.hero-brief {
  max-width: 680px;
  margin: 0 auto 2rem;
  line-height: 1.8;
  color: var(--color-text);
}

.hero-actions {
  align-items: center;
  display: flex;
  gap: 0.65rem;
  justify-content: center;
}

.btn-compact {
  font-size: 0.82rem;
  padding: 0.35rem 0.8rem;
}

.about-modal {
  align-items: center;
  background: rgba(17, 24, 39, 0.72);
  display: flex;
  inset: 0;
  justify-content: center;
  padding: clamp(0.75rem, 2vw, 1.5rem);
  position: fixed;
  z-index: 200;
}

.about-modal-content {
  display: flex;
  flex-direction: column;
  max-height: calc(100vh - 3rem);
  max-height: min(760px, 85dvh);
  max-width: min(820px, calc(100vw - 3rem));
  overflow: hidden;
  padding: 0;
  width: 100%;
}

.about-modal-header {
  align-items: flex-start;
  border-bottom: 1px solid var(--color-border);
  display: flex;
  flex: 0 0 auto;
  gap: 1rem;
  justify-content: space-between;
  padding: 1.25rem 1.5rem;
}

.about-modal-header h2 {
  color: var(--color-primary);
  font-family: var(--font-serif);
  font-size: 1.4rem;
  min-width: 0;
  overflow-wrap: anywhere;
}

.about-modal-body {
  min-height: 0;
  overflow-y: auto;
  overscroll-behavior: contain;
  padding: 1.5rem;
  scrollbar-gutter: stable;
}

.about-modal-close {
  align-items: center;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: 999px;
  cursor: pointer;
  display: flex;
  font-size: 1.25rem;
  height: 2rem;
  justify-content: center;
  line-height: 1;
  flex: 0 0 2rem;
  width: 2rem;
}

@media (max-width: 600px) {
  .about-modal-content {
    max-width: calc(100vw - 1.5rem);
  }

  .about-modal-header,
  .about-modal-body {
    padding: 1rem;
  }
}
</style>
