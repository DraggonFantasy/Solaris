<template>
  <div class="reader-page">
    <BackLink :fallback="{ name: 'dialogue-detail', params: { id: route.params.id } }" />
    <div v-if="loading" class="text-muted">{{ t('common.loading') }}</div>
    <div v-else-if="errorStatus !== null" class="card reader-error">
      <h1>{{ unavailable ? t('dialogue.notAvailableTitle') : t('common.error') }}</h1>
      <p>{{ unavailable ? t('dialogue.notAvailableText') : t('dialogue.loadErrorText') }}</p>
    </div>
    <template v-else-if="dialogue">
      <header class="reader-header">
        <p class="text-muted">{{ dialogue.section_name }} · {{ t('dialogue.internalTitle') }}</p>
        <h1 class="page-title">{{ dialogue.title }}</h1>
      </header>
      <article v-if="dialogue.text?.trim()" class="card reader-text">
        <MarkdownRenderer :content="dialogue.text" />
      </article>
      <div v-else class="card reader-empty">
        <p>{{ t('dialogue.internalUnavailable') }}</p>
        <a v-if="dialogue.source_url" :href="dialogue.source_url" class="btn btn-outline" target="_blank" rel="noopener noreferrer">
          {{ t('dialogue.openExternal') }} ↗
        </a>
      </div>
    </template>
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import api from '../api'
import BackLink from '../components/BackLink.vue'
import MarkdownRenderer from '../components/MarkdownRenderer.vue'

const route = useRoute()
const { t } = useI18n()
const dialogue = ref(null)
const loading = ref(true)
const errorStatus = ref(null)
const unavailable = computed(() => [403, 404].includes(errorStatus.value))

watch(() => route.params.id, async (id, previousId, onCleanup) => {
  let active = true
  onCleanup(() => { active = false })
  loading.value = true
  dialogue.value = null
  errorStatus.value = null
  try {
    const { data } = await api.get(`/dialogues/${id}/`)
    if (active) dialogue.value = data
  } catch (error) {
    if (active) errorStatus.value = error.response?.status || 0
  } finally {
    if (active) loading.value = false
  }
}, { immediate: true })
</script>

<style scoped>
.reader-page { max-width: 900px; margin: 0 auto; }
.reader-header { margin-bottom: 1.5rem; }
.reader-header p { margin-bottom: 0.5rem; }
.reader-text { overflow-wrap: anywhere; }
.reader-empty p, .reader-error p { color: var(--color-text-muted); margin-bottom: 1rem; }
.reader-error h1 { font-family: var(--font-serif); font-size: 1.5rem; margin-bottom: 0.75rem; }
</style>
