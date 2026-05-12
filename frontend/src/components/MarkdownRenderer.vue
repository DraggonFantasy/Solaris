<template>
  <div class="markdown-body" v-html="rendered" />
</template>

<script setup>
import { computed } from 'vue'
import { marked } from 'marked'

const props = defineProps({
  content: { type: String, default: '' },
})

const rendered = computed(() => marked.parse(props.content || ''))
</script>

<style scoped>
.markdown-body {
  font-family: var(--font-serif);
  font-size: 0.9375rem;
  line-height: 1.85;
  color: var(--color-text);
}

.markdown-body :deep(h2) {
  font-size: 1rem;
  font-weight: 700;
  margin: 1.5rem 0 0.5rem;
  color: var(--color-primary);
  border-bottom: 1px solid var(--color-border);
  padding-bottom: 0.25rem;
}

.markdown-body :deep(h3) {
  font-size: 0.9375rem;
  font-weight: 700;
  margin: 1.25rem 0 0.4rem;
}

.markdown-body :deep(p) {
  margin-bottom: 0.875rem;
}

.markdown-body :deep(h2 ~ p),
.markdown-body :deep(h2 ~ ul),
.markdown-body :deep(h2 ~ ol),
.markdown-body :deep(h2 ~ blockquote),
.markdown-body :deep(h2 ~ pre),
.markdown-body :deep(h2 ~ h3) {
  margin-left: 1rem;
}

.markdown-body :deep(strong) {
  font-weight: 700;
}

.markdown-body :deep(em) {
  font-style: italic;
}

.markdown-body :deep(blockquote) {
  border-left: 3px solid var(--color-accent);
  padding-left: 1rem;
  color: var(--color-text-muted);
  margin: 1rem 0;
}

.markdown-body :deep(code) {
  background: var(--color-bg);
  padding: 0.15em 0.4em;
  border-radius: 3px;
  font-size: 0.875em;
  font-family: 'Courier New', monospace;
}

.markdown-body :deep(pre) {
  background: var(--color-bg);
  padding: 1rem;
  border-radius: var(--radius);
  overflow-x: auto;
  margin: 1rem 0;
}

.markdown-body :deep(hr) {
  border: none;
  border-top: 1px solid var(--color-border);
  margin: 1.5rem 0;
}

.markdown-body :deep(ul),
.markdown-body :deep(ol) {
  padding-left: 1.5rem;
  margin-bottom: 0.875rem;
}

.markdown-body :deep(li) {
  margin-bottom: 0.25rem;
}

@media (max-width: 640px) {
  .markdown-body :deep(h2 ~ p),
  .markdown-body :deep(h2 ~ ul),
  .markdown-body :deep(h2 ~ ol),
  .markdown-body :deep(h2 ~ blockquote),
  .markdown-body :deep(h2 ~ pre),
  .markdown-body :deep(h2 ~ h3) {
    margin-left: 0.625rem;
  }
}
</style>
