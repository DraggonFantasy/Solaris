<template>
  <div class="create-page">
    <h1 class="page-title">{{ t('dialogue.createTitle') }}</h1>

    <!-- Step indicator -->
    <div class="steps">
      <div
        v-for="(step, i) in steps"
        :key="i"
        class="step"
        :class="{ active: currentStep === i, done: currentStep > i }"
      >
        <div class="step-circle">{{ currentStep > i ? '✓' : i + 1 }}</div>
        <span class="step-label">{{ step }}</span>
      </div>
      <div class="step-line" />
    </div>

    <div class="wizard-body card">

      <!-- Step 0: Context -->
      <div v-if="currentStep === 0">
        <h2 class="step-title">{{ t('dialogue.step1Title') }}</h2>

        <div class="form-group">
          <label>{{ t('dialogue.section') }} *</label>
          <select v-model="form.section" required>
            <option value="" disabled>— {{ t('dialogue.selectSection') }} —</option>
            <option v-for="s in sections" :key="s.id" :value="s.id">{{ s.name }}</option>
          </select>
        </div>

        <div class="form-group">
          <label>{{ t('dialogue.title') }} *</label>
          <input v-model="form.title" type="text" :placeholder="t('dialogue.titlePlaceholder')" required />
        </div>

        <div class="form-row">
          <div class="form-group">
            <label>{{ t('dialogue.llmName') }}</label>
            <input v-model="form.llm_name" type="text" placeholder="Claude, Gemini, GPT-4…" />
          </div>
          <div class="form-group">
            <label>{{ t('dialogue.llmVersion') }}</label>
            <input v-model="form.llm_version" type="text" placeholder="3.5 Sonnet, 1.5 Pro…" />
          </div>
        </div>

        <div class="form-group">
          <label>{{ t('dialogue.style') }}</label>
          <select v-model="form.style">
            <option value="other">{{ t('dialogue.styleOther') }}</option>
            <option value="socratic">{{ t('dialogue.styleSocratic') }}</option>
            <option value="dialectical">{{ t('dialogue.styleDialectical') }}</option>
            <option value="rhetorical">{{ t('dialogue.styleRhetorical') }}</option>
            <option value="debate">{{ t('dialogue.styleDebate') }}</option>
          </select>
        </div>
      </div>

      <!-- Step 1: Dialogue text -->
      <div v-if="currentStep === 1">
        <h2 class="step-title">{{ t('dialogue.step2Title') }}</h2>
        <p class="step-hint">{{ t('dialogue.step2Hint') }}</p>
        <MarkdownEditor
          v-model="form.text"
          :placeholder="dialoguePlaceholder"
        />
      </div>

      <!-- Step 2: Extras -->
      <div v-if="currentStep === 2">
        <h2 class="step-title">{{ t('dialogue.step3Title') }}</h2>

        <div class="form-group">
          <label>{{ t('dialogues.summary') }}</label>
          <textarea v-model="form.summary" rows="3" :placeholder="t('dialogue.summaryPlaceholder')" />
        </div>

        <div class="form-group">
          <label>{{ t('dialogues.foodForThought') }}</label>
          <textarea v-model="form.food_for_thought" rows="3" :placeholder="t('dialogue.foodPlaceholder')" />
        </div>

        <div class="form-group">
          <label>{{ t('dialogues.literature') }}</label>
          <textarea v-model="form.recommended_literature" rows="3" :placeholder="t('dialogue.literaturePlaceholder')" />
        </div>

        <div v-if="error" class="alert alert-error">{{ error }}</div>
      </div>

    </div>

    <!-- Navigation -->
    <div class="wizard-nav">
      <button v-if="currentStep > 0" class="btn btn-outline" @click="currentStep--">
        ← {{ t('common.back') }}
      </button>
      <div class="nav-right">
        <button
          v-if="currentStep < steps.length - 1"
          class="btn btn-primary"
          :disabled="!canProceed"
          @click="nextStep"
        >
          {{ t('dialogue.next') }} →
        </button>
        <template v-else>
          <button class="btn btn-outline" :disabled="submitting" @click="submit(false)">
            {{ t('dialogue.saveDraft') }}
          </button>
          <button class="btn btn-primary" :disabled="submitting" @click="submit(true)">
            {{ submitting ? t('common.loading') : t('dialogue.submitReview') }}
          </button>
        </template>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import api from '../api'
import MarkdownEditor from '../components/MarkdownEditor.vue'

const { t } = useI18n()
const router = useRouter()

const currentStep = ref(0)
const submitting = ref(false)
const error = ref('')
const sections = ref([])

const steps = computed(() => [
  t('dialogue.step1'),
  t('dialogue.step2'),
  t('dialogue.step3'),
])

const form = ref({
  section: '',
  title: '',
  llm_name: '',
  llm_version: '',
  style: 'other',
  text: '',
  summary: '',
  food_for_thought: '',
  recommended_literature: '',
})

const dialoguePlaceholder = `## Human

Write your message here...


## AI

Write the AI response here...
`

const canProceed = computed(() => {
  if (currentStep.value === 0) return form.value.section && form.value.title.trim()
  if (currentStep.value === 1) return form.value.text.trim().length > 50
  return true
})

onMounted(async () => {
  const { data } = await api.get('/sections/')
  sections.value = data.results || data
})

function nextStep() {
  if (canProceed.value) currentStep.value++
}

async function submit(submitForReview) {
  error.value = ''
  submitting.value = true
  try {
    const payload = { ...form.value, published: false }
    const { data } = await api.post('/dialogues/', payload)
    if (submitForReview) {
      router.push({ name: 'dialogue-submitted', params: { id: data.id } })
    } else {
      router.push({ name: 'my-dialogues' })
    }
  } catch (err) {
    error.value = err.response?.data
      ? JSON.stringify(err.response.data)
      : t('common.error')
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.steps {
  display: flex;
  align-items: center;
  margin-bottom: 2rem;
  position: relative;
}

.step-line {
  position: absolute;
  top: 18px;
  left: 0;
  right: 0;
  height: 2px;
  background: var(--color-border);
  z-index: 0;
}

.step {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.4rem;
  flex: 1;
  z-index: 1;
}

.step-circle {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  border: 2px solid var(--color-border);
  background: var(--color-surface);
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 600;
  font-size: 0.875rem;
  color: var(--color-text-muted);
  transition: all 0.2s;
}

.step.active .step-circle {
  border-color: var(--color-primary);
  background: var(--color-primary);
  color: white;
}

.step.done .step-circle {
  border-color: var(--color-success);
  background: var(--color-success);
  color: white;
}

.step-label {
  font-size: 0.75rem;
  color: var(--color-text-muted);
  font-weight: 500;
}

.step.active .step-label {
  color: var(--color-primary);
}

.wizard-body {
  min-height: 400px;
  margin-bottom: 1.5rem;
}

.step-title {
  font-family: var(--font-serif);
  font-size: 1.125rem;
  color: var(--color-primary);
  margin-bottom: 1.5rem;
}

.step-hint {
  font-size: 0.875rem;
  color: var(--color-text-muted);
  margin-bottom: 1rem;
}

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
}

.wizard-nav {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.nav-right {
  display: flex;
  gap: 0.75rem;
}
</style>
