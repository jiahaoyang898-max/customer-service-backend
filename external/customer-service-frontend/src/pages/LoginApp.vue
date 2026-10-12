<script setup>
/**
 * 电商小二 · 登录 / 注册页
 * ------------------------------------------------------------
 * 设计语言：浅色商务风（参考 Apple / 智枢项目视觉规范）
 *   · 系统字体栈 SF Pro / PingFang
 *   · 满屏通铺双栏布局，无外边距、无卡片浮层
 *   · 主色 #0071e3，文字 #1d1d1f / #6e6e73
 * 本组件为独立多页面入口，不改动原有 App.vue 的任何逻辑。
 */
import { computed, onMounted, ref } from 'vue'
import { accountExists, getRememberedAccount, login as submitLoginRequest, register as submitRegisterRequest } from './auth'

// ---------- 状态 ----------
const mode = ref('login') // login | register
const submitting = ref(false)
const notice = ref(null) // { type: 'success' | 'error', text }
const errors = ref({})

const loginForm = ref({ account: '', password: '', remember: true })
const registerForm = ref({ name: '', account: '', password: '', confirm: '', agree: false })

const showLoginPassword = ref(false)
const showRegisterPassword = ref(false)

const isLogin = computed(() => mode.value === 'login')
const submitLabel = computed(() => (isLogin.value ? '登 录' : '注 册'))

// ---------- 静态内容 ----------
const features = [
  {
    title: '大模型意图理解',
    desc: '基于 LLM 的多轮对话引擎，精准识别业务诉求',
    icon: '<path d="M12 3a9 9 0 1 0 4.6 16.74L21 21l-1.2-4.3A9 9 0 0 0 12 3Z"/><path d="M9 11h6M9 15h4"/>',
  },
  {
    title: '订单物流一体化',
    desc: '订单状态、物流轨迹、退款申请，一处直达',
    icon: '<path d="M4 7.5 12 3l8 4.5v9L12 21l-8-4.5v-9Z"/><path d="M4 7.5 12 12l8-4.5M12 12v9"/>',
  },
  {
    title: '数字人语音播报',
    desc: '3D 数字人实时应答，支持语音合成播报',
    icon: '<circle cx="12" cy="8" r="3.2"/><path d="M5.5 20c0-3.6 2.9-6.5 6.5-6.5s6.5 2.9 6.5 6.5"/>',
  },
]

// ---------- 校验规则 ----------
const ACCOUNT_RE = /^(1[3-9]\d{9}|[^\s@]+@[^\s@.]+(\.[^\s@.]+)+)$/

function validateLogin() {
  const next = {}
  const account = loginForm.value.account.trim()
  if (!account) next.account = '请输入手机号或邮箱'
  else if (!ACCOUNT_RE.test(account)) next.account = '请输入有效的手机号或邮箱地址'

  if (!loginForm.value.password) next.password = '请输入密码'
  else if (loginForm.value.password.length < 6) next.password = '密码至少 6 位'

  errors.value = next
  return Object.keys(next).length === 0
}

function validateRegister() {
  const next = {}
  const { name, account, password, confirm, agree } = registerForm.value
  const trimmedAccount = account.trim()

  if (!name.trim()) next.name = '请设置昵称'
  else if (name.trim().length > 20) next.name = '昵称请控制在 20 字以内'

  if (!trimmedAccount) next.account = '请输入手机号或邮箱'
  else if (!ACCOUNT_RE.test(trimmedAccount)) next.account = '请输入有效的手机号或邮箱地址'
  else if (accountExists(trimmedAccount)) next.account = '该账号已被注册，可直接登录'

  if (!password) next.password = '请设置密码'
  else if (password.length < 6) next.password = '密码至少 6 位'
  else if (!/[A-Za-z]/.test(password) || !/\d/.test(password)) next.password = '密码需同时包含字母和数字'

  if (!confirm) next.confirm = '请再次输入密码'
  else if (confirm !== password) next.confirm = '两次输入的密码不一致'

  if (!agree) next.agree = '请先阅读并同意用户协议与隐私政策'

  errors.value = next
  return Object.keys(next).length === 0
}

// ---------- 交互 ----------
function switchMode(next) {
  if (mode.value === next) return
  mode.value = next
  notice.value = null
  errors.value = {}
  try {
    history.replaceState(null, '', next === 'register' ? '#register' : '#login')
  } catch {
    /* 忽略 */
  }
}

function handleForgot() {
  notice.value = { type: 'error', text: '如需重置密码，请联系系统管理员。' }
}

async function handleLogin() {
  notice.value = null
  if (!validateLogin()) return

  submitting.value = true
  await delay(520) // 模拟网络请求
  const result = submitLoginRequest({ ...loginForm.value })
  submitting.value = false

  if (!result.ok) {
    notice.value = { type: 'error', text: result.message }
    return
  }

  notice.value = { type: 'success', text: `欢迎回来，${result.session.name}！正在进入工作台…` }
  await delay(700)
  // 登录成功后进入原有工作台首页
  window.location.href = '/'
}

async function handleRegister() {
  notice.value = null
  if (!validateRegister()) return

  submitting.value = true
  await delay(620)
  const created = submitRegisterRequest({
    name: registerForm.value.name,
    account: registerForm.value.account,
    password: registerForm.value.password,
  })
  submitting.value = false

  // 注册成功 → 切回登录并预填账号
  loginForm.value.account = created.account
  loginForm.value.password = ''
  loginForm.value.remember = true
  registerForm.value = { name: '', account: '', password: '', confirm: '', agree: false }
  switchMode('login')
  notice.value = { type: 'success', text: '注册成功！请使用刚设置的密码登录。' }
}

function clearError(field) {
  if (errors.value[field]) {
    const next = { ...errors.value }
    delete next[field]
    errors.value = next
  }
}

function delay(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

// ---------- 初始化 ----------
onMounted(() => {
  const remembered = getRememberedAccount()
  if (remembered) loginForm.value.account = remembered
  if (window.location.hash === '#register') mode.value = 'register'
})
</script>

<template>
  <div class="auth-page">
    <main class="auth-shell">
      <!-- ==================== 左：品牌区（铺满左半屏） ==================== -->
      <section class="brand">
        <header class="brand__head">
          <span class="logo">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"
                 stroke-linecap="round" stroke-linejoin="round">
              <path d="M21 11.5a8.4 8.4 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.4 8.4 0 0 1-3.8-.9L3 21l1.9-5.7a8.4 8.4 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.4 8.4 0 0 1 3.8-.9h.5a8.5 8.5 0 0 1 8 8v.5Z" />
            </svg>
          </span>
          <div class="brand__title">
            <strong>电商小二</strong>
            <span>Smart Service Platform</span>
          </div>
        </header>

        <div class="brand__body">
          <h1 class="brand__slogan">
            智能客服<br />
            <em>工作台</em>
          </h1>
          <p class="brand__lead">
            大模型驱动的电商客服中枢，一站式处理订单、物流与售后咨询。
          </p>

          <ul class="features">
            <li v-for="item in features" :key="item.title" class="feature">
              <span class="feature__icon">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"
                     stroke-linecap="round" stroke-linejoin="round" v-html="item.icon"></svg>
              </span>
              <span class="feature__text">
                <strong>{{ item.title }}</strong>
                <span>{{ item.desc }}</span>
              </span>
            </li>
          </ul>
        </div>

        <footer class="brand__foot">
          <span>© 2026 电商小二</span>
          <span class="dot"></span>
          <span>v1.0</span>
        </footer>
      </section>

      <!-- ==================== 右：表单区（铺满右半屏） ==================== -->
      <section class="panel">
        <div class="panel__inner">
          <div class="panel__head">
            <h2>{{ isLogin ? '欢迎回来' : '创建账号' }}</h2>
            <p>{{ isLogin ? '登录后继续使用智能客服工作台' : '注册后即可体验完整的客服对话流程' }}</p>
          </div>

          <!-- 登录 / 注册 切换 -->
          <div class="segmented" role="tablist">
            <span :class="{ 'is-right': !isLogin }" class="segmented__thumb"></span>
            <button
              :class="{ 'is-active': isLogin }"
              role="tab"
              type="button"
              @click="switchMode('login')"
            >
              登录
            </button>
            <button
              :class="{ 'is-active': !isLogin }"
              role="tab"
              type="button"
              @click="switchMode('register')"
            >
              注册
            </button>
          </div>

          <!-- 提示条 -->
          <Transition name="notice">
            <p v-if="notice" :class="`notice notice--${notice.type}`">
              <span class="notice__icon">{{ notice.type === 'success' ? '✓' : '!' }}</span>
              <span>{{ notice.text }}</span>
            </p>
          </Transition>

          <!-- ---------- 登录表单 ---------- -->
          <form v-if="isLogin" class="form" novalidate @submit.prevent="handleLogin">
            <label class="field" :class="{ 'has-error': errors.account }">
              <span class="field__label">账号</span>
              <span class="field__control">
                <svg class="field__icon" viewBox="0 0 24 24" fill="none" stroke="currentColor"
                     stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
                  <circle cx="12" cy="7" r="4" />
                </svg>
                <input
                  v-model="loginForm.account"
                  autocomplete="username"
                  placeholder="手机号 或 邮箱"
                  type="text"
                  @input="clearError('account')"
                />
              </span>
              <span v-if="errors.account" class="field__error">{{ errors.account }}</span>
            </label>

            <label class="field" :class="{ 'has-error': errors.password }">
              <span class="field__label">密码</span>
              <span class="field__control">
                <svg class="field__icon" viewBox="0 0 24 24" fill="none" stroke="currentColor"
                     stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">
                  <rect x="4" y="10.5" width="16" height="10" rx="2.5" />
                  <path d="M8 10.5V7.5a4 4 0 0 1 8 0v3" />
                </svg>
                <input
                  v-model="loginForm.password"
                  :type="showLoginPassword ? 'text' : 'password'"
                  autocomplete="current-password"
                  placeholder="请输入登录密码"
                  @input="clearError('password')"
                />
                <button
                  :aria-label="showLoginPassword ? '隐藏密码' : '显示密码'"
                  class="field__toggle"
                  type="button"
                  @click="showLoginPassword = !showLoginPassword"
                >
                  <svg v-if="showLoginPassword" viewBox="0 0 24 24" fill="none" stroke="currentColor"
                       stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M2 12s3.6-6.5 10-6.5S22 12 22 12s-3.6 6.5-10 6.5S2 12 2 12Z" />
                    <circle cx="12" cy="12" r="3" />
                  </svg>
                  <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"
                       stroke-linecap="round" stroke-linejoin="round">
                    <path d="M4 4l16 16M10.6 6.1A9.9 9.9 0 0 1 12 6c6.4 0 10 6 10 6a17.6 17.6 0 0 1-3.4 4M6.6 8.3A17.5 17.5 0 0 0 2 12s3.6 6.5 10 6.5c1.2 0 2.3-.2 3.3-.6" />
                  </svg>
                </button>
              </span>
              <span v-if="errors.password" class="field__error">{{ errors.password }}</span>
            </label>

            <div class="form__row">
              <label class="checkbox">
                <input v-model="loginForm.remember" type="checkbox" />
                <span>记住我</span>
              </label>
              <button class="link" type="button" @click="handleForgot">忘记密码？</button>
            </div>

            <button :disabled="submitting" class="submit" type="submit">
              <span v-if="submitting" class="spinner"></span>
              <span>{{ submitting ? '登录中…' : submitLabel }}</span>
            </button>
          </form>

          <!-- ---------- 注册表单 ---------- -->
          <form v-else class="form" novalidate @submit.prevent="handleRegister">
            <label class="field" :class="{ 'has-error': errors.name }">
              <span class="field__label">昵称</span>
              <span class="field__control">
                <svg class="field__icon" viewBox="0 0 24 24" fill="none" stroke="currentColor"
                     stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
                  <circle cx="12" cy="7" r="4" />
                </svg>
                <input
                  v-model="registerForm.name"
                  autocomplete="nickname"
                  placeholder="用于展示的称呼"
                  type="text"
                  @input="clearError('name')"
                />
              </span>
              <span v-if="errors.name" class="field__error">{{ errors.name }}</span>
            </label>

            <label class="field" :class="{ 'has-error': errors.account }">
              <span class="field__label">账号</span>
              <span class="field__control">
                <svg class="field__icon" viewBox="0 0 24 24" fill="none" stroke="currentColor"
                     stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">
                  <rect x="3" y="5" width="18" height="14" rx="2.5" />
                  <path d="m4 7.5 8 5 8-5" />
                </svg>
                <input
                  v-model="registerForm.account"
                  autocomplete="username"
                  placeholder="手机号 或 邮箱"
                  type="text"
                  @input="clearError('account')"
                />
              </span>
              <span v-if="errors.account" class="field__error">{{ errors.account }}</span>
            </label>

            <label class="field" :class="{ 'has-error': errors.password }">
              <span class="field__label">密码</span>
              <span class="field__control">
                <svg class="field__icon" viewBox="0 0 24 24" fill="none" stroke="currentColor"
                     stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">
                  <rect x="4" y="10.5" width="16" height="10" rx="2.5" />
                  <path d="M8 10.5V7.5a4 4 0 0 1 8 0v3" />
                </svg>
                <input
                  v-model="registerForm.password"
                  :type="showRegisterPassword ? 'text' : 'password'"
                  autocomplete="new-password"
                  placeholder="6 位以上，包含字母和数字"
                  @input="clearError('password')"
                />
                <button
                  :aria-label="showRegisterPassword ? '隐藏密码' : '显示密码'"
                  class="field__toggle"
                  type="button"
                  @click="showRegisterPassword = !showRegisterPassword"
                >
                  <svg v-if="showRegisterPassword" viewBox="0 0 24 24" fill="none" stroke="currentColor"
                       stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M2 12s3.6-6.5 10-6.5S22 12 22 12s-3.6 6.5-10 6.5S2 12 2 12Z" />
                    <circle cx="12" cy="12" r="3" />
                  </svg>
                  <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"
                       stroke-linecap="round" stroke-linejoin="round">
                    <path d="M4 4l16 16M10.6 6.1A9.9 9.9 0 0 1 12 6c6.4 0 10 6 10 6a17.6 17.6 0 0 1-3.4 4M6.6 8.3A17.5 17.5 0 0 0 2 12s3.6 6.5 10 6.5c1.2 0 2.3-.2 3.3-.6" />
                  </svg>
                </button>
              </span>
              <span v-if="errors.password" class="field__error">{{ errors.password }}</span>
            </label>

            <label class="field" :class="{ 'has-error': errors.confirm }">
              <span class="field__label">确认密码</span>
              <span class="field__control">
                <svg class="field__icon" viewBox="0 0 24 24" fill="none" stroke="currentColor"
                     stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M20 6 9 17l-5-5" />
                </svg>
                <input
                  v-model="registerForm.confirm"
                  :type="showRegisterPassword ? 'text' : 'password'"
                  autocomplete="new-password"
                  placeholder="请再次输入密码"
                  @input="clearError('confirm')"
                />
              </span>
              <span v-if="errors.confirm" class="field__error">{{ errors.confirm }}</span>
            </label>

            <label class="checkbox checkbox--agree" :class="{ 'has-error': errors.agree }">
              <input v-model="registerForm.agree" type="checkbox" @change="clearError('agree')" />
              <span>
                我已阅读并同意
                <button class="link" type="button">《用户协议》</button>
                与
                <button class="link" type="button">《隐私政策》</button>
              </span>
            </label>
            <span v-if="errors.agree" class="field__error checkbox__error">{{ errors.agree }}</span>

            <button :disabled="submitting" class="submit" type="submit">
              <span v-if="submitting" class="spinner"></span>
              <span>{{ submitting ? '注册中…' : submitLabel }}</span>
            </button>
          </form>

          <p class="panel__foot">
            {{ isLogin ? '还没有账号？' : '已经有账号了？' }}
            <button class="link link--strong" type="button" @click="switchMode(isLogin ? 'register' : 'login')">
              {{ isLogin ? '立即注册' : '返回登录' }}
            </button>
          </p>
        </div>
      </section>
    </main>
  </div>
</template>

<style scoped>
/* ============================================================
   基础变量：延续智枢项目 / 本项目的苹果风设计规范
   ============================================================ */
.auth-page {
  --ink: #1d1d1f;
  --ink-soft: #6e6e73;
  --ink-faint: #a1a1a6;
  --line: rgba(0, 0, 0, 0.08);
  --line-soft: rgba(0, 0, 0, 0.05);
  --accent: #0071e3;
  --accent-strong: #0a84ff;
  --accent-soft: rgba(0, 113, 227, 0.12);
  --danger: #e0245e;
  --success: #11b388;
  --font: -apple-system, BlinkMacSystemFont, 'SF Pro Display', 'SF Pro Text', 'PingFang SC',
    'Helvetica Neue', 'Microsoft YaHei', 'Segoe UI', sans-serif;

  position: relative;
  min-height: 100vh;
  padding: 0;
  margin: 0;
  overflow: hidden;
  font-family: var(--font);
  color: var(--ink);
  background: #ffffff;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

:global(html),
:global(body) {
  margin: 0;
  padding: 0;
  background: #ffffff;
}
:global(#app) {
  min-height: 100vh;
}
:global(*) {
  box-sizing: border-box;
}

/* ============================================================
   主布局：满屏通铺双栏（无外边距 / 无卡片浮层）
   ============================================================ */
.auth-shell {
  width: 100%;
  min-height: 100vh;
  display: grid;
  grid-template-columns: 1fr 1fr;
  background: #ffffff;
}

/* ============================================================
   左：品牌区（铺满左半屏）
   ============================================================ */
.brand {
  position: relative;
  padding: 64px 72px 48px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  gap: 40px;
  overflow: hidden;
  background:
    radial-gradient(820px 620px at 86% 2%, rgba(0, 113, 227, 0.13), transparent 62%),
    radial-gradient(680px 560px at 2% 100%, rgba(17, 179, 136, 0.11), transparent 60%),
    linear-gradient(165deg, #f6fafe 0%, #ecf3fb 55%, #e4eef9 100%);
  border-right: 1px solid var(--line-soft);
}
/* 品牌区底纹：极淡网格，融入背景而非独立浮层 */
.brand::before {
  content: '';
  position: absolute;
  right: -130px;
  bottom: -170px;
  width: 660px;
  height: 660px;
  pointer-events: none;
  background-image:
    linear-gradient(rgba(120, 140, 170, 0.08) 1px, transparent 1px),
    linear-gradient(90deg, rgba(120, 140, 170, 0.08) 1px, transparent 1px);
  background-size: 44px 44px;
  -webkit-mask-image: radial-gradient(circle at 68% 68%, #000 0%, transparent 72%);
  mask-image: radial-gradient(circle at 68% 68%, #000 0%, transparent 72%);
}
.brand > * {
  position: relative;
  z-index: 1;
  max-width: 560px;
}

.brand__head {
  display: flex;
  align-items: center;
  gap: 13px;
}
.logo {
  width: 46px;
  height: 46px;
  border-radius: 14px;
  display: grid;
  place-items: center;
  color: #fff;
  flex-shrink: 0;
  background: linear-gradient(140deg, var(--accent-strong), #0062cc);
  box-shadow:
    0 10px 22px -10px rgba(0, 113, 227, 0.72),
    inset 0 1px 0 rgba(255, 255, 255, 0.35);
}
.logo svg {
  width: 24px;
  height: 24px;
}
.brand__title {
  display: flex;
  flex-direction: column;
  line-height: 1.25;
}
.brand__title strong {
  font-size: 18px;
  font-weight: 600;
  letter-spacing: 0.2px;
  color: var(--ink);
}
.brand__title span {
  font-size: 11.5px;
  font-weight: 400;
  letter-spacing: 0.6px;
  color: var(--ink-faint);
  text-transform: uppercase;
}

/* 中部文案：竖向居中，撑满可用高度 */
.brand__body {
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: center;
}

.brand__slogan {
  margin: 0 0 18px;
  font-size: 50px;
  line-height: 1.12;
  font-weight: 600;
  letter-spacing: -0.025em;
  color: var(--ink);
}
.brand__slogan em {
  font-style: normal;
  background: linear-gradient(96deg, var(--accent-strong), #11b388);
  -webkit-background-clip: text;
  background-clip: text;
  -webkit-text-fill-color: transparent;
}
.brand__lead {
  margin: 0 0 40px;
  max-width: 34ch;
  font-size: 15.5px;
  line-height: 1.75;
  color: var(--ink-soft);
}

.features {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 20px;
}
.feature {
  display: flex;
  align-items: flex-start;
  gap: 13px;
}
.feature__icon {
  width: 38px;
  height: 38px;
  border-radius: 11px;
  display: grid;
  place-items: center;
  flex-shrink: 0;
  color: var(--accent);
  background: rgba(255, 255, 255, 0.92);
  border: 1px solid rgba(0, 113, 227, 0.14);
  box-shadow: 0 4px 12px -6px rgba(0, 113, 227, 0.34);
}
.feature__icon svg {
  width: 19px;
  height: 19px;
}
.feature__text {
  display: flex;
  flex-direction: column;
  gap: 3px;
  padding-top: 2px;
}
.feature__text strong {
  font-size: 14.5px;
  font-weight: 600;
  color: var(--ink);
}
.feature__text span {
  font-size: 12.5px;
  line-height: 1.55;
  color: var(--ink-soft);
}

.brand__foot {
  display: flex;
  align-items: center;
  gap: 9px;
  font-size: 12px;
  color: var(--ink-faint);
}
.brand__foot .dot {
  width: 3px;
  height: 3px;
  border-radius: 50%;
  background: currentColor;
  opacity: 0.6;
}

/* ============================================================
   右：表单区（铺满右半屏，内容居中）
   ============================================================ */
.panel {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 56px 72px;
  background: #ffffff;
}
.panel__inner {
  width: 100%;
  max-width: 430px;
}

.panel__head h2 {
  margin: 0 0 8px;
  font-size: 29px;
  font-weight: 600;
  letter-spacing: -0.015em;
  color: var(--ink);
}
.panel__head p {
  margin: 0 0 28px;
  font-size: 13.5px;
  color: var(--ink-soft);
}

/* ---------- 分段控件 ---------- */
.segmented {
  position: relative;
  display: grid;
  grid-template-columns: 1fr 1fr;
  padding: 4px;
  margin-bottom: 24px;
  background: #f0f1f4;
  border-radius: 13px;
}
.segmented__thumb {
  position: absolute;
  top: 4px;
  left: 4px;
  width: calc(50% - 4px);
  height: calc(100% - 8px);
  border-radius: 10px;
  background: #fff;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1), 0 0 0 0.5px rgba(0, 0, 0, 0.03);
  transition: transform 0.34s cubic-bezier(0.16, 1, 0.3, 1);
}
.segmented__thumb.is-right {
  transform: translateX(100%);
}
.segmented button {
  position: relative;
  z-index: 1;
  height: 36px;
  border: 0;
  background: transparent;
  border-radius: 10px;
  font-family: inherit;
  font-size: 14px;
  font-weight: 500;
  color: var(--ink-soft);
  cursor: pointer;
  transition: color 0.24s ease;
}
.segmented button.is-active {
  color: var(--ink);
  font-weight: 600;
}

/* ---------- 提示条 ---------- */
.notice {
  display: flex;
  align-items: flex-start;
  gap: 9px;
  margin: 0 0 18px;
  padding: 11px 14px;
  border-radius: 12px;
  font-size: 13px;
  line-height: 1.55;
}
.notice__icon {
  flex-shrink: 0;
  width: 17px;
  height: 17px;
  margin-top: 0.5px;
  border-radius: 50%;
  display: grid;
  place-items: center;
  font-size: 11px;
  font-weight: 700;
  color: #fff;
}
.notice--success {
  color: #0b6b53;
  background: rgba(17, 179, 136, 0.1);
  border: 1px solid rgba(17, 179, 136, 0.22);
}
.notice--success .notice__icon {
  background: var(--success);
}
.notice--error {
  color: #a3143f;
  background: rgba(224, 36, 94, 0.08);
  border: 1px solid rgba(224, 36, 94, 0.2);
}
.notice--error .notice__icon {
  background: var(--danger);
}
.notice-enter-active,
.notice-leave-active {
  transition: opacity 0.24s ease, transform 0.24s ease;
}
.notice-enter-from,
.notice-leave-to {
  opacity: 0;
  transform: translateY(-6px);
}

/* ---------- 表单 ---------- */
.form {
  display: flex;
  flex-direction: column;
  gap: 15px;
}
.field {
  display: flex;
  flex-direction: column;
  gap: 7px;
}
.field__label {
  font-size: 12.5px;
  font-weight: 500;
  color: var(--ink-soft);
  letter-spacing: 0.2px;
}
.field__control {
  position: relative;
  display: block;
}
.field__icon {
  position: absolute;
  left: 13px;
  top: 50%;
  transform: translateY(-50%);
  width: 17px;
  height: 17px;
  color: var(--ink-faint);
  pointer-events: none;
  transition: color 0.2s ease;
}
.field__control input {
  width: 100%;
  height: 47px;
  padding: 0 44px 0 39px;
  border-radius: 12px;
  border: 1px solid rgba(0, 0, 0, 0.12);
  background: #f5f5f7;
  font-family: inherit;
  font-size: 14.5px;
  color: var(--ink);
  transition: border-color 0.18s ease, box-shadow 0.18s ease, background 0.18s ease;
}
.field__control input::placeholder {
  color: var(--ink-faint);
}
.field__control input:hover {
  background: #f1f2f5;
}
.field__control input:focus {
  outline: none;
  background: #fff;
  border-color: var(--accent);
  box-shadow: 0 0 0 3.5px var(--accent-soft);
}
.field__control:focus-within .field__icon {
  color: var(--accent);
}
.field__toggle {
  position: absolute;
  right: 8px;
  top: 50%;
  transform: translateY(-50%);
  width: 32px;
  height: 32px;
  display: grid;
  place-items: center;
  border: 0;
  border-radius: 9px;
  background: transparent;
  color: var(--ink-faint);
  cursor: pointer;
  transition: color 0.18s ease, background 0.18s ease;
}
.field__toggle svg {
  width: 17px;
  height: 17px;
}
.field__toggle:hover {
  color: var(--ink-soft);
  background: rgba(0, 0, 0, 0.04);
}
.field__error {
  font-size: 12px;
  color: var(--danger);
  line-height: 1.45;
}
.field.has-error .field__control input {
  border-color: rgba(224, 36, 94, 0.5);
  background: rgba(224, 36, 94, 0.04);
}

/* ---------- 记住我 / 协议 ---------- */
.form__row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: -2px;
}
.checkbox {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: var(--ink-soft);
  cursor: pointer;
  user-select: none;
}
.checkbox input {
  appearance: none;
  -webkit-appearance: none;
  width: 17px;
  height: 17px;
  margin: 0;
  flex-shrink: 0;
  border-radius: 5px;
  border: 1.5px solid rgba(0, 0, 0, 0.2);
  background: #fff;
  cursor: pointer;
  position: relative;
  transition: background 0.18s ease, border-color 0.18s ease;
}
.checkbox input:hover {
  border-color: rgba(0, 0, 0, 0.32);
}
.checkbox input:checked {
  background: var(--accent);
  border-color: var(--accent);
}
.checkbox input:checked::after {
  content: '';
  position: absolute;
  left: 4.6px;
  top: 1.2px;
  width: 4.5px;
  height: 9px;
  border: 2px solid #fff;
  border-top: 0;
  border-left: 0;
  transform: rotate(43deg);
}
.checkbox--agree {
  align-items: flex-start;
  gap: 9px;
  margin-top: 2px;
  line-height: 1.6;
  font-size: 12.5px;
}
.checkbox--agree input {
  margin-top: 1.5px;
}
.checkbox.has-error input {
  border-color: var(--danger);
}
.checkbox__error {
  display: block;
  margin-top: -9px;
}

.link {
  border: 0;
  padding: 0;
  background: transparent;
  font-family: inherit;
  font-size: inherit;
  color: var(--accent);
  cursor: pointer;
  transition: opacity 0.18s ease;
}
.link:hover {
  opacity: 0.72;
  text-decoration: underline;
  text-underline-offset: 3px;
}
.link--strong {
  font-size: 13.5px;
  font-weight: 600;
}

/* ---------- 提交按钮 ---------- */
.submit {
  position: relative;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 9px;
  height: 50px;
  margin-top: 5px;
  border: 0;
  border-radius: 13px;
  background: linear-gradient(180deg, var(--accent-strong), #0066d6);
  color: #fff;
  font-family: inherit;
  font-size: 15.5px;
  font-weight: 600;
  letter-spacing: 0.4px;
  cursor: pointer;
  box-shadow:
    0 10px 22px -10px rgba(0, 113, 227, 0.62),
    inset 0 1px 0 rgba(255, 255, 255, 0.24);
  transition: transform 0.18s cubic-bezier(0.16, 1, 0.3, 1), box-shadow 0.24s ease;
}
.submit:hover:not(:disabled) {
  transform: translateY(-1.5px);
  box-shadow:
    0 16px 30px -10px rgba(0, 113, 227, 0.66),
    inset 0 1px 0 rgba(255, 255, 255, 0.24);
}
.submit:active:not(:disabled) {
  transform: translateY(0) scale(0.994);
}
.submit:disabled {
  opacity: 0.62;
  cursor: not-allowed;
}
.spinner {
  width: 15px;
  height: 15px;
  border-radius: 50%;
  border: 2px solid rgba(255, 255, 255, 0.4);
  border-top-color: #fff;
  animation: spin 0.7s linear infinite;
}
@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

/* ---------- 底部切换 ---------- */
.panel__foot {
  margin: 24px 0 0;
  text-align: center;
  font-size: 13px;
  color: var(--ink-soft);
}

/* ============================================================
   响应式
   ============================================================ */
@media (max-width: 1024px) {
  .auth-shell {
    grid-template-columns: 1fr;
  }
  .brand {
    padding: 40px 40px 34px;
    gap: 28px;
    border-right: 0;
    border-bottom: 1px solid var(--line-soft);
  }
  .brand > * {
    max-width: none;
  }
  .brand__body {
    flex: initial;
  }
  .brand__slogan {
    font-size: 36px;
  }
  .brand__lead {
    margin-bottom: 0;
  }
  .features {
    display: none;
  }
  .brand__foot {
    display: none;
  }
  .panel {
    padding: 44px 40px 56px;
  }
}

@media (max-width: 560px) {
  .brand {
    padding: 30px 24px 26px;
  }
  .brand__slogan {
    font-size: 28px;
  }
  .brand__lead {
    font-size: 13.5px;
  }
  .panel {
    padding: 32px 24px 44px;
  }
  .panel__head h2 {
    font-size: 24px;
  }
}
</style>
