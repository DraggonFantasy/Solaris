<template>
  <div class="home">
    <section class="hero">
      <div class="hero-content">
        <img class="hero-logo" src="/logo.png" alt="Солярис" />
        <h1 class="hero-title">СОЛЯРИС</h1>
        <p class="hero-tagline">{{ t('home.tagline') }}</p>
        <p class="hero-brief">{{ t('home.brief') }}</p>
        <button type="button" class="btn btn-primary" @click="showAbout = true">
          {{ t('home.aboutProject') }}
        </button>
      </div>
    </section>

    <div v-if="showAbout" class="about-modal" role="dialog" aria-modal="true" @click.self="showAbout = false">
      <div class="about-modal-content card">
        <button type="button" class="about-modal-close" :aria-label="t('common.close')" @click="showAbout = false">
          ×
        </button>
        <h2>{{ t('home.aboutProject') }}</h2>
        <MarkdownRenderer :content="t('home.aboutText')" />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import MarkdownRenderer from '../components/MarkdownRenderer.vue'

const { t } = useI18n()
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

.about-modal {
  align-items: center;
  background: rgba(17, 24, 39, 0.72);
  display: flex;
  inset: 0;
  justify-content: center;
  padding: 1.5rem;
  position: fixed;
  z-index: 50;
}

.about-modal-content {
  max-height: calc(100vh - 3rem);
  max-width: min(820px, calc(100vw - 3rem));
  overflow: auto;
  padding: 2rem;
  position: relative;
}

.about-modal-content h2 {
  color: var(--color-primary);
  font-family: var(--font-serif);
  font-size: 1.4rem;
  margin-bottom: 1rem;
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
  position: absolute;
  right: 1rem;
  top: 1rem;
  width: 2rem;
}
</style>
