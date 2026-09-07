const assert = require('node:assert/strict')
const { readFileSync } = require('node:fs')
const { resolve } = require('node:path')
const { test } = require('node:test')
const { runInNewContext } = require('node:vm')
const { parse, compileScript } = require('@vue/compiler-sfc')
const { transformSync } = require('esbuild')
const { renderToString } = require('@vue/server-renderer')
const vue = require('vue')

function loadComponent(path, modules, inlineTemplate = false) {
  const filename = resolve(__dirname, '../src', path)
  const { descriptor } = parse(readFileSync(filename, 'utf8'), { filename })
  const script = compileScript(descriptor, { id: 'navigation-test', inlineTemplate })
  const { code } = transformSync(script.content, { format: 'cjs' })
  const module = { exports: {} }
  runInNewContext(code, {
    module, exports: module.exports,
    require: (id) => {
      assert.ok(id in modules, `Unexpected import: ${id}`)
      return modules[id]
    },
  })
  return module.exports.default
}

function routerAt(...entries) {
  const stack = [...entries]
  const route = vue.reactive({ fullPath: stack.at(-1), params: { id: '42' } })
  const router = {
    options: { history: { get state() { return { back: stack.at(-2) || null } } } },
    resolve(target) {
      const href = typeof target === 'string' ? target : `/dialogues/${target.params.id}${target.name === 'dialogue-reader' ? '/read' : ''}`
      return { href, matched: href.startsWith('/unknown') ? [] : [{}] }
    },
    back() { stack.pop(); route.fullPath = stack.at(-1) },
    push(target) { stack.push(router.resolve(target).href); route.fullPath = stack.at(-1) },
    replace(target) { stack[stack.length - 1] = router.resolve(target).href; route.fullPath = stack.at(-1) },
  }
  return { router, route, stack }
}

function backLink(context, fallback = '/sections') {
  return loadComponent('components/BackLink.vue', {
    vue,
    'vue-router': { useRoute: () => context.route, useRouter: () => context.router },
    'vue-i18n': { useI18n: () => ({ t: (key) => key }) },
  }).setup({ fallback }, { expose() {} })
}

function click(overrides = {}) {
  return { button: 0, defaultPrevented: false, preventDefault() { this.defaultPrevented = true }, ...overrides }
}

test('Back returns to the actual source, including its query and hash', () => {
  for (const source of ['/communications', '/sections/archive', '/moderation/dialogues?status=submitted#queue', '/sections/worldview']) {
    const context = routerAt(source, '/dialogues/42')
    const link = backLink(context)
    assert.equal(link.href.value, source)
    link.goBack(click())
    assert.equal(context.route.fullPath, source)
    assert.equal(context.stack.length, 1)
  }
})

test('reader → card → original queue pops history without a navigation loop', () => {
  const context = routerAt('/communications', '/dialogues/42', '/dialogues/42/read')
  backLink(context, '/dialogues/42').goBack(click())
  assert.equal(context.route.fullPath, '/dialogues/42')
  backLink(context).goBack(click())
  assert.equal(context.route.fullPath, '/communications')
  assert.equal(context.stack.length, 1)
})

test('direct entry and unusable history use the local fallback', () => {
  for (const previous of [null, 'https://example.com', '//example.com', '/unknown', '/dialogues/42/read']) {
    const entries = previous ? [previous, '/dialogues/42/read'] : ['/dialogues/42/read']
    const context = routerAt(...entries)
    const link = backLink(context, '/dialogues/42')
    assert.equal(link.href.value, '/dialogues/42')
    link.goBack(click())
    assert.equal(context.route.fullPath, '/dialogues/42')
    assert.equal(context.stack.length, entries.length)
  }
})

test('modified clicks retain normal link behavior', () => {
  const context = routerAt('/communications', '/dialogues/42')
  const link = backLink(context)
  for (const modifiers of [{ ctrlKey: true }, { metaKey: true }, { shiftKey: true }, { button: 1 }]) {
    const event = click(modifiers)
    link.goBack(event)
    assert.equal(event.defaultPrevented, false)
    assert.equal(context.route.fullPath, '/dialogues/42')
  }
})

async function renderDialogueView(path, data, failure) {
  const context = routerAt('/sections/worldview', '/dialogues/42')
  const mounted = []
  const auth = { isStaff: false, isAuthenticated: false }
  const empty = { render: () => null }
  const modules = {
    vue: { ...vue, onMounted: (callback) => mounted.push(callback) },
    'vue-router': { useRoute: () => context.route, useRouter: () => context.router },
    'vue-i18n': { useI18n: () => ({ t: (key) => key }) },
    '../stores/auth': { useAuthStore: () => auth },
    '../api': { __esModule: true, default: { async get(url) {
      assert.equal(url, '/dialogues/42/')
      if (failure) throw failure
      return { data }
    } } },
    '../components/BackLink.vue': empty,
    '../components/DialogueComments.vue': empty,
    '../components/DialogueImportWarning.vue': empty,
    '../components/DialogueResourcesModal.vue': empty,
    '../components/MarkdownRenderer.vue': { props: ['content'], setup: (props) => () => vue.h('div', props.content) },
  }
  const component = loadComponent(path, modules, true)
  const scope = vue.effectScope()
  try {
    const render = scope.run(() => component.setup({}, { expose() {} }))
    await Promise.all(mounted.map((callback) => callback()))
    await new Promise(setImmediate)
    const app = vue.createSSRApp({ setup: () => render })
    app.component('RouterLink', {
      props: ['to'],
      setup: (props, { slots }) => () => vue.h('a', { href: context.router.resolve(props.to).href }, slots.default?.()),
    })
    return await renderToString(app)
  } finally {
    scope.stop()
  }
}

const dialogue = {
  id: 42, title: 'Dialogue title', section_name: 'Worldview', section_slug: 'worldview',
  status: 'published', created_at: '2026-09-07', text: 'INTERNAL_DIALOGUE_TEXT',
  source_url: 'https://claude.ai/share/example',
}

test('dialogue card links to the separate reader and does not embed the text', async () => {
  const html = await renderDialogueView('views/DialogueDetailView.vue', dialogue)
  assert.ok(html.includes('href="/dialogues/42/read"'))
  assert.ok(!html.includes('INTERNAL_DIALOGUE_TEXT'))
  assert.ok(!html.includes('#internal-dialogue'))
})

test('external-only dialogue has no internal-reader button', async () => {
  const html = await renderDialogueView('views/DialogueDetailView.vue', { ...dialogue, text: '' })
  assert.ok(!html.includes('/dialogues/42/read'))
  assert.ok(html.includes(dialogue.source_url))
})

test('reader displays the stored dialogue text on its own page', async () => {
  const html = await renderDialogueView('views/DialogueReaderView.vue', dialogue)
  assert.ok(html.includes('INTERNAL_DIALOGUE_TEXT'))
  assert.ok(html.includes('Dialogue title'))
})

test('direct reader URL handles absent internal text', async () => {
  const html = await renderDialogueView('views/DialogueReaderView.vue', { ...dialogue, text: '' })
  assert.ok(html.includes('dialogue.internalUnavailable'))
  assert.ok(html.includes(dialogue.source_url))
})

test('reader respects API denial without showing dialogue content', async () => {
  const html = await renderDialogueView('views/DialogueReaderView.vue', null, { response: { status: 404 } })
  assert.ok(html.includes('dialogue.notAvailableTitle'))
  assert.ok(!html.includes('INTERNAL_DIALOGUE_TEXT'))
})
