<template>
  <a :href="href" class="back-link" @click="goBack">← {{ t('common.back') }}</a>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'

const props = defineProps({ fallback: { type: [String, Object], required: true } })
const route = useRoute()
const router = useRouter()
const { t } = useI18n()

const previous = computed(() => {
  const currentPath = route.fullPath
  const back = router.options.history.state.back
  if (typeof back !== 'string' || !back.startsWith('/') || back.startsWith('//')) return null
  if (back === currentPath || !router.resolve(back).matched.length) return null
  return back
})
const href = computed(() => router.resolve(previous.value || props.fallback).href)

function goBack(event) {
  if (event.defaultPrevented || event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return
  event.preventDefault()
  // Pop history so returning from the reader does not create a card/reader loop.
  if (previous.value) router.back()
  else router.replace(props.fallback)
}
</script>

<style scoped>
.back-link {
  color: var(--color-text-muted);
  display: inline-block;
  font-size: 0.875rem;
  margin-bottom: 1rem;
  text-decoration: none;
}
.back-link:hover { color: var(--color-primary); }
</style>
