const assert = require('node:assert/strict')
const { readFileSync } = require('node:fs')
const { resolve } = require('node:path')
const { test } = require('node:test')
const { runInNewContext } = require('node:vm')
const { parse, compileScript } = require('@vue/compiler-sfc')
const { transformSync } = require('esbuild')
const vue = require('vue')

// Execute the actual form's setup and submission with mocked API/navigation.
const filename = resolve(__dirname, '../src/views/CreateDialogueView.vue')
const { descriptor } = parse(readFileSync(filename, 'utf8'), { filename })
const script = compileScript(descriptor, { id: 'dialogue-import-test' })
const { code } = transformSync(script.content, { format: 'cjs' })

function formWithImport(importResponse) {
  const calls = []
  const navigation = []
  const api = {
    async post(url, body) {
      calls.push({ url, body })
      if (url === '/dialogues/import-share/') return importResponse()
      assert.equal(url, '/dialogues/')
      return { data: { ...body, id: 42 } }
    },
    async patch(url, body) {
      calls.push({ url, body })
      return { data: { ...body, id: 42 } }
    },
  }
  const modules = {
    vue: { ...vue, onMounted() {}, watch() {} },
    'vue-router': {
      useRoute: () => ({ name: 'create-dialogue', query: {}, params: {} }),
      useRouter: () => ({ push: (target) => navigation.push(target) }),
    },
    'vue-i18n': { useI18n: () => ({ t: (key) => key }) },
    '../stores/auth': { useAuthStore: () => ({ isStaff: false }) },
    '../api': { default: api, __esModule: true },
    '../components/MarkdownEditor.vue': {},
  }
  const module = { exports: {} }
  runInNewContext(code, {
    module, exports: module.exports,
    require: (id) => {
      assert.ok(id in modules, `Unexpected import: ${id}`)
      return modules[id]
    },
    URL, crypto: require('node:crypto').webcrypto,
    localStorage: { setItem() {} },
  })
  const state = module.exports.default.setup({}, { expose() {} })
  Object.assign(state.form.value, {
    section: 1, title: 'Dialogue', source_url: 'https://claude.ai/share/new',
  })
  state.authors.value = [{ kind: 'person', name: 'Author' }]
  return { state, calls, navigation }
}

test('failed import submits the external link and reason for moderation', async () => {
  const { state, calls, navigation } = formWithImport(async () => {
    throw { response: { data: { detail: 'External resource returned HTTP 403.' } } }
  })
  await state.submit(true)
  const creation = calls.find((call) => call.url === '/dialogues/').body
  assert.equal(creation.import_error, 'External resource returned HTTP 403.')
  assert.equal(creation.text, '')
  assert.equal(creation.source_url, 'https://claude.ai/share/new')
  assert.equal(calls.at(-1).body.status, 'submitted')
  assert.equal(navigation.at(-1).name, 'dialogue-submitted')
  assert.equal(state.error.value, '')
})

test('changed URL and failed import cannot submit text from the previous URL', async () => {
  const { state, calls } = formWithImport(async () => { throw new Error('Network Error') })
  state.form.value.text = 'Old dialogue text'
  state.importedSourceUrl.value = 'https://claude.ai/share/old'
  await state.submit(true)
  const creation = calls.find((call) => call.url === '/dialogues/').body
  assert.equal(creation.text, '')
  assert.equal(creation.import_error, 'Network Error')
})

test('successful retry stores internal text and clears the failure reason', async () => {
  let failed = true
  const { state, calls } = formWithImport(async () => {
    if (failed) throw new Error('timeout')
    return { data: { markdown: '## Claude\n\nAnswer', service: 'claude' } }
  })
  await state.ensureInternalDialogueCopy()
  assert.equal(state.importError.value, 'timeout')
  failed = false
  await state.submit(true)
  const creation = calls.find((call) => call.url === '/dialogues/').body
  assert.equal(creation.import_error, '')
  assert.equal(creation.text, '## Claude\n\nAnswer')
})

test('empty imported text still submits the link with an explanatory error', async () => {
  const { state, calls } = formWithImport(async () => ({ data: { markdown: '  ' } }))
  await state.submit(true)
  const creation = calls.find((call) => call.url === '/dialogues/').body
  assert.equal(creation.text, '')
  assert.equal(creation.import_error, 'dialogue.importEmpty')
  assert.equal(calls.at(-1).body.status, 'submitted')
})
