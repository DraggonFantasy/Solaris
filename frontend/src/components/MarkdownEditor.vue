<template>
  <div class="md-editor">
    <div class="md-toolbar">
      <button type="button" title="Bold" @click="insert('**', '**', 'bold text')">B</button>
      <button type="button" title="Italic" @click="insert('*', '*', 'italic text')"><em>I</em></button>
      <button type="button" title="Heading 2" @click="insertLine('## ', 'Heading')">H2</button>
      <button type="button" title="Heading 3" @click="insertLine('### ', 'Heading')">H3</button>
      <button type="button" title="Blockquote" @click="insertLine('> ', 'quote')">❝</button>
      <button type="button" title="Code" @click="insert('`', '`', 'code')">{ }</button>
      <div class="toolbar-divider" />
      <button
        type="button"
        class="preview-toggle"
        :class="{ active: showPreview }"
        @click="showPreview = !showPreview"
      >{{ showPreview ? 'Edit' : 'Preview' }}</button>
    </div>

    <div class="md-body" :class="{ split: showPreview }">
      <textarea
        ref="textarea"
        class="md-textarea"
        :value="modelValue"
        :placeholder="placeholder"
        @input="$emit('update:modelValue', $event.target.value)"
        @keydown.tab.prevent="onTab"
      />
      <div v-if="showPreview" class="md-preview" v-html="rendered" />
    </div>

    <div class="md-footer">
      <span class="char-count">{{ modelValue.length }} chars</span>
      <span class="md-hint">Markdown supported</span>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { marked } from 'marked'

const props = defineProps({
  modelValue: { type: String, default: '' },
  placeholder: { type: String, default: '' },
})
const emit = defineEmits(['update:modelValue'])

const textarea = ref(null)
const showPreview = ref(false)

const rendered = computed(() => marked.parse(props.modelValue || ''))

function getSelection() {
  const el = textarea.value
  return { start: el.selectionStart, end: el.selectionEnd }
}

function applyValue(newVal, newCursor) {
  emit('update:modelValue', newVal)
  // Restore cursor after Vue re-renders
  requestAnimationFrame(() => {
    textarea.value.focus()
    textarea.value.setSelectionRange(newCursor, newCursor)
  })
}

function insert(before, after, placeholder) {
  const el = textarea.value
  const { start, end } = getSelection()
  const selected = props.modelValue.slice(start, end) || placeholder
  const newVal =
    props.modelValue.slice(0, start) +
    before + selected + after +
    props.modelValue.slice(end)
  applyValue(newVal, start + before.length + selected.length + after.length)
}

function insertLine(prefix, placeholder) {
  const el = textarea.value
  const { start } = getSelection()
  const lineStart = props.modelValue.lastIndexOf('\n', start - 1) + 1
  const newVal =
    props.modelValue.slice(0, lineStart) +
    prefix + (props.modelValue.slice(lineStart) || placeholder)
  applyValue(newVal, lineStart + prefix.length + (props.modelValue.slice(lineStart) ? 0 : placeholder.length))
}

function onTab() {
  insert('  ', '', '')
}
</script>

<style scoped>
.md-editor {
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  overflow: hidden;
  display: flex;
  flex-direction: column;
  background: var(--color-surface);
}

.md-toolbar {
  display: flex;
  align-items: center;
  gap: 2px;
  padding: 0.4rem 0.5rem;
  border-bottom: 1px solid var(--color-border);
  background: var(--color-bg);
  flex-wrap: wrap;
}

.md-toolbar button {
  background: none;
  border: 1px solid transparent;
  border-radius: 4px;
  padding: 0.2rem 0.5rem;
  cursor: pointer;
  font-size: 0.875rem;
  font-family: var(--font-sans);
  color: var(--color-text);
  transition: background 0.15s, border-color 0.15s;
  min-width: 28px;
}

.md-toolbar button:hover {
  background: var(--color-border);
  border-color: var(--color-border);
}

.toolbar-divider {
  width: 1px;
  height: 20px;
  background: var(--color-border);
  margin: 0 4px;
}

.preview-toggle {
  margin-left: auto;
  font-weight: 500;
  color: var(--color-primary) !important;
}

.preview-toggle.active {
  background: var(--color-primary) !important;
  color: white !important;
}

.md-body {
  display: flex;
  min-height: 360px;
}

.md-body.split .md-textarea {
  width: 50%;
  border-right: 1px solid var(--color-border);
}

.md-textarea {
  width: 100%;
  min-height: 360px;
  padding: 1rem;
  border: none;
  outline: none;
  resize: vertical;
  font-family: 'Courier New', monospace;
  font-size: 0.9rem;
  line-height: 1.7;
  color: var(--color-text);
  background: var(--color-surface);
}

.md-preview {
  width: 50%;
  padding: 1rem 1.25rem;
  overflow-y: auto;
  font-family: var(--font-serif);
  font-size: 0.9375rem;
  line-height: 1.85;
  color: var(--color-text);
}

.md-preview :deep(h2) {
  font-size: 1rem;
  font-weight: 700;
  margin: 1.25rem 0 0.5rem;
  color: var(--color-primary);
  border-bottom: 1px solid var(--color-border);
  padding-bottom: 0.25rem;
}

.md-preview :deep(h3) {
  font-size: 0.9375rem;
  font-weight: 700;
  margin: 1rem 0 0.4rem;
}

.md-preview :deep(p) {
  margin-bottom: 0.75rem;
}

.md-preview :deep(blockquote) {
  border-left: 3px solid var(--color-accent);
  padding-left: 1rem;
  color: var(--color-text-muted);
  margin: 0.75rem 0;
}

.md-preview :deep(code) {
  background: var(--color-bg);
  padding: 0.1em 0.3em;
  border-radius: 3px;
  font-size: 0.875em;
}

.md-footer {
  display: flex;
  justify-content: space-between;
  padding: 0.3rem 0.75rem;
  font-size: 0.75rem;
  color: var(--color-text-muted);
  border-top: 1px solid var(--color-border);
  background: var(--color-bg);
}
</style>
