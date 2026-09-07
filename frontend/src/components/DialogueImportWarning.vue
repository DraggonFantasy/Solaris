<template>
  <div v-if="auth.isStaff && error" class="alert alert-info import-warning" role="status">
    <strong>{{ t('dialogue.importFailedTitle') }}</strong>
    <p>{{ error }}</p>
    <p>{{ t('dialogue.importFailedHint') }}</p>
  </div>
</template>

<script setup>
import { useI18n } from 'vue-i18n'
import { useAuthStore } from '../stores/auth'

defineProps({ error: { type: String, default: '' } })
const { t } = useI18n()
const auth = useAuthStore()
</script>

<style scoped>
.import-warning { margin-top: 0.75rem; overflow-wrap: anywhere; }
.import-warning p { margin-top: 0.35rem; white-space: pre-wrap; }
</style>
