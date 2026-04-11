<template>
  <div class="lang-switcher">
    <button
      v-for="lang in languages"
      :key="lang.code"
      class="lang-btn"
      :class="{ active: locale === lang.code }"
      @click="switchLang(lang.code)"
    >
      {{ lang.label }}
    </button>
  </div>
</template>

<script setup>
import { useI18n } from 'vue-i18n'

const { locale } = useI18n()

const languages = [
  { code: 'uk', label: 'УК' },
  { code: 'en', label: 'EN' },
]

function switchLang(code) {
  locale.value = code
  localStorage.setItem('locale', code)
}
</script>

<style scoped>
.lang-switcher {
  display: flex;
  gap: 2px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  overflow: hidden;
}

.lang-btn {
  background: none;
  border: none;
  padding: 0.25rem 0.5rem;
  font-size: 0.75rem;
  font-weight: 600;
  cursor: pointer;
  color: var(--color-text-muted);
  transition: background 0.15s, color 0.15s;
}

.lang-btn:hover {
  background: var(--color-bg);
  color: var(--color-text);
}

.lang-btn.active {
  background: var(--color-primary);
  color: white;
}
</style>
