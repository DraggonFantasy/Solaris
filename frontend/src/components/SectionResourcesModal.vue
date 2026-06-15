<template>
  <div v-if="open" class="resource-modal" role="dialog" aria-modal="true" @click.self="$emit('close')">
    <div class="resource-modal-content card">
      <button type="button" class="resource-modal-close" :aria-label="t('common.close')" @click="$emit('close')">
        ×
      </button>
      <h2>{{ title }}</h2>

      <div v-if="loading" class="text-muted">{{ t('common.loading') }}</div>
      <div v-else-if="!items.length" class="text-muted">{{ t('sections.noResources') }}</div>

      <div v-else-if="type === 'literature'" class="resource-list">
        <article v-for="(item, index) in items" :key="`${item.dialogue_id}-${index}`" class="resource-item">
          <h3>{{ item.dialogue_title }}</h3>
          <p>{{ item.text }}</p>
        </article>
      </div>

      <div v-else-if="type === 'authors'" class="resource-list">
        <article v-for="item in authorItems" :key="item.key" class="resource-item">
          <h3>
            {{ item.name }}
            <small v-if="item.version">{{ item.version }}</small>
          </h3>
          <p v-if="item.description">{{ item.description }}</p>
          <ul class="author-dialogues">
            <li v-for="dialogue in item.dialogues" :key="dialogue.id">
              <RouterLink :to="`/dialogues/${dialogue.id}`">
                {{ dialogue.title }}
              </RouterLink>
            </li>
          </ul>
        </article>
      </div>

      <div v-else-if="type === 'illustrations'" class="illustration-resource-grid">
        <figure v-for="item in items" :key="item.id" class="illustration-resource">
          <img :src="item.image" :alt="item.caption" />
          <figcaption>
            <strong>{{ item.dialogue_title }}</strong>
            <span v-if="item.caption">{{ item.caption }}</span>
          </figcaption>
        </figure>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'

const props = defineProps({
  open: { type: Boolean, default: false },
  type: { type: String, default: 'literature' },
  title: { type: String, default: '' },
  resources: { type: Object, default: () => ({}) },
  loading: { type: Boolean, default: false },
})

defineEmits(['close'])

const { t } = useI18n()
const items = computed(() => props.resources?.[props.type] || [])
const authorItems = computed(() => {
  const groups = new Map()
  items.value.forEach((item) => {
    const name = (item.name || '').trim()
    if (!name) return
    const version = (item.version || '').trim()
    const description = (item.description || '').trim()
    const kind = (item.kind || '').trim()
    const key = [kind, name, version, description].join('::').toLowerCase()
    if (!groups.has(key)) {
      groups.set(key, {
        key,
        name,
        version,
        description,
        dialogues: [],
      })
    }
    const group = groups.get(key)
    if (!group.dialogues.some((dialogue) => dialogue.id === item.dialogue_id)) {
      group.dialogues.push({
        id: item.dialogue_id,
        title: item.dialogue_title,
      })
    }
  })
  return Array.from(groups.values()).sort((a, b) => a.name.localeCompare(b.name))
})
</script>

<style scoped>
.resource-modal {
  align-items: center;
  background: rgba(17, 24, 39, 0.72);
  display: flex;
  inset: 0;
  justify-content: center;
  padding: 1.5rem;
  position: fixed;
  z-index: 60;
}

.resource-modal-content {
  max-height: calc(100vh - 3rem);
  max-width: min(860px, calc(100vw - 3rem));
  overflow: auto;
  padding: 2rem;
  position: relative;
  width: 100%;
}

.resource-modal-close {
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

.resource-modal-content h2 {
  color: var(--color-primary);
  font-family: var(--font-serif);
  font-size: 1.35rem;
  margin-bottom: 1rem;
  padding-right: 2.5rem;
}

.resource-list {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.resource-item {
  border-bottom: 1px solid var(--color-border);
  padding-bottom: 1rem;
}

.resource-item:last-child {
  border-bottom: 0;
  padding-bottom: 0;
}

.resource-item h3 {
  color: var(--color-text);
  font-family: var(--font-serif);
  font-size: 1rem;
  margin-bottom: 0.35rem;
}

.resource-item small {
  color: var(--color-text-muted);
  font-family: var(--font-sans);
  font-size: 0.78rem;
  font-weight: 500;
}

.resource-item p {
  color: var(--color-text-muted);
  line-height: 1.7;
  white-space: pre-wrap;
}

.resource-source {
  color: var(--color-accent);
  font-size: 0.8rem;
  font-weight: 600;
  margin-bottom: 0.35rem;
}

.author-dialogues {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  margin: 0.55rem 0 0;
  padding-left: 1.1rem;
}

.author-dialogues a {
  color: var(--color-accent);
  font-size: 0.86rem;
  font-weight: 600;
  text-decoration: none;
}

.author-dialogues a:hover {
  text-decoration: underline;
}

.illustration-resource-grid {
  display: grid;
  gap: 1rem;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
}

.illustration-resource {
  margin: 0;
}

.illustration-resource img {
  background: var(--color-bg);
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  display: block;
  height: 150px;
  object-fit: contain;
  width: 100%;
}

.illustration-resource figcaption {
  color: var(--color-text-muted);
  display: flex;
  flex-direction: column;
  font-size: 0.84rem;
  gap: 0.25rem;
  line-height: 1.5;
  margin-top: 0.5rem;
}

.illustration-resource strong {
  color: var(--color-text);
}
</style>
