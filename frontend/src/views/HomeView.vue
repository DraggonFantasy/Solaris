<template>
  <div class="home">
    <section class="hero">
      <div class="hero-content">
        <h1 class="hero-title">СОЛЯРИС</h1>
        <p class="hero-tagline">{{ t('home.tagline') }}</p>
        <p class="hero-brief">{{ t('home.brief') }}</p>
        <RouterLink class="btn btn-primary" to="/sections">{{ t('home.explore') }}</RouterLink>
      </div>
    </section>

    <section v-if="recentDialogues.length" class="recent">
      <h2 class="section-heading">{{ t('home.recentDialogues') }}</h2>
      <div class="dialogue-grid">
        <RouterLink
          v-for="d in recentDialogues"
          :key="d.id"
          :to="`/dialogues/${d.id}`"
          class="dialogue-card card"
        >
          <div class="dialogue-section">{{ d.section_name }}</div>
          <h3 class="dialogue-title">{{ d.title }}</h3>
          <p v-if="d.summary" class="dialogue-summary">{{ d.summary }}</p>
          <div class="dialogue-meta">
            <span>{{ d.human_author_username }}</span>
            <span v-if="d.llm_name">· {{ d.llm_name }}</span>
            <span class="spacer" />
            <span>♥ {{ d.likes_count }}</span>
          </div>
        </RouterLink>
      </div>
    </section>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import api from '../api'

const { t } = useI18n()
const recentDialogues = ref([])

onMounted(async () => {
  try {
    const { data } = await api.get('/dialogues/?page_size=6')
    recentDialogues.value = data.results || data
  } catch {
    // ignore
  }
})
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

.section-heading {
  font-family: var(--font-serif);
  font-size: 1.5rem;
  margin-bottom: 1.5rem;
  color: var(--color-text);
}

.dialogue-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 1.25rem;
}

.dialogue-card {
  text-decoration: none;
  color: inherit;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  transition: box-shadow 0.2s, transform 0.2s;
}

.dialogue-card:hover {
  box-shadow: var(--shadow-md);
  transform: translateY(-2px);
}

.dialogue-section {
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--color-accent);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.dialogue-title {
  font-family: var(--font-serif);
  font-size: 1rem;
  font-weight: 700;
  line-height: 1.4;
}

.dialogue-summary {
  font-size: 0.875rem;
  color: var(--color-text-muted);
  flex: 1;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.dialogue-meta {
  display: flex;
  font-size: 0.8rem;
  color: var(--color-text-muted);
  gap: 0.4rem;
  margin-top: 0.5rem;
}

.spacer { flex: 1; }
</style>
