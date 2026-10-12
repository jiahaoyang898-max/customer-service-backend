<script setup>
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { getSession, logout } from './pages/auth.js'
// 卡通文字头像：用内嵌 SVG 保证所有平台一致，不依赖外部图片
function createAvatarSvg(text, type = 'user') {
  const colors =
    type === 'user'
      ? { from: '#C8F6D8', to: '#A2E9C6' }
      : type === 'digital'
        ? { from: '#D6F0FF', to: '#A8D8FF' }
        : { from: '#D4ECFF', to: '#B4DFFF' }
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="120" height="120" viewBox="0 0 120 120">
    <defs>
      <linearGradient id="avt" x1="0" y1="0" x2="1" y2="1">
        <stop offset="0%" stop-color="${colors.from}"/>
        <stop offset="100%" stop-color="${colors.to}"/>
      </linearGradient>
    </defs>
    <circle cx="60" cy="60" r="60" fill="url(#avt)"/>
    <text x="60" y="66" font-family="Arial Rounded MT Bold, Nunito, PingFang SC, Microsoft YaHei, sans-serif" font-size="52" font-weight="700" fill="#ffffff" text-anchor="middle">${text}</text>
  </svg>`
  return `data:image/svg+xml;base64,${btoa(unescape(encodeURIComponent(svg)))}`
}

const senderId = ref('u1001')
const draftMessage = ref('')
const isSending = ref(false)
const errorMessage = ref('')
const messages = ref([])
const messagesContainer = ref(null)

const orders = ref([])
const products = ref([])
const isLoadingSidebar = ref(false)
const sidebarError = ref('')
const activeTab = ref('orders')

// ── 登录态 / 退出登录 ──────────────────────────────────────────────
const session = ref(getSession())
const sessionName = computed(() => session.value?.name || '未登录')
const sessionAccount = computed(() => session.value?.account || '')
const userInitial = computed(() => String(sessionName.value).trim().charAt(0) || '用')
const loggingOut = ref(false)

function handleLogout() {
  if (loggingOut.value) return
  if (!window.confirm('确定要退出登录吗？')) return
  loggingOut.value = true
  logout()
  session.value = null
  window.location.href = '/login'
}

// TTS state
const ttsState = ref({})
let currentAudio = null

// Copy state
const copyState = ref({})

// ── Canvas 粒子背景系统 ──────────────────────────────────────────────
const bgCanvas = ref(null)
let animFrameId = null
let bgParticles = []
const BG_PARTICLE_COUNT = 80
const BG_CONNECT_DIST = 150
const BG_MOUSE_RADIUS = 180
const bgMouse = { x: null, y: null }

function createBgParticles(w, h) {
  const palette = [
    [13, 148, 136], [20, 184, 166], [245, 158, 11],
    [217, 119, 6], [2, 132, 199], [56, 189, 248],
  ]
  bgParticles = Array.from({ length: BG_PARTICLE_COUNT }, () => {
    const color = palette[Math.floor(Math.random() * palette.length)]
    return {
      x: Math.random() * w, y: Math.random() * h,
      size: Math.random() * 2.5 + 1,
      vx: (Math.random() - 0.5) * 0.35,
      vy: (Math.random() - 0.5) * 0.35,
      color, opacity: Math.random() * 0.45 + 0.12,
      phase: Math.random() * Math.PI * 2,
      pulse: Math.random() * 0.015 + 0.005,
    }
  })
}

function animateBg(ctx, w, h, time) {
  ctx.clearRect(0, 0, w, h)

  for (const p of bgParticles) {
    p.x += p.vx + Math.sin(time * 0.001 + p.phase) * 0.25
    p.y += p.vy + Math.cos(time * 0.001 + p.phase + 1) * 0.25

    if (bgMouse.x !== null) {
      const dx = p.x - bgMouse.x, dy = p.y - bgMouse.y
      const dist = Math.hypot(dx, dy)
      if (dist < BG_MOUSE_RADIUS) {
        const force = (BG_MOUSE_RADIUS - dist) / BG_MOUSE_RADIUS
        p.x += (dx / dist) * force * 0.7
        p.y += (dy / dist) * force * 0.7
      }
    }

    if (p.x < -20) p.x = w + 20; if (p.x > w + 20) p.x = -20
    if (p.y < -20) p.y = h + 20; if (p.y > h + 20) p.y = -20
  }

  // 连线
  ctx.lineWidth = 0.5
  for (let i = 0; i < bgParticles.length; i++) {
    for (let j = i + 1; j < bgParticles.length; j++) {
      const dx = bgParticles[i].x - bgParticles[j].x
      const dy = bgParticles[i].y - bgParticles[j].y
      const dist = Math.hypot(dx, dy)
      if (dist < BG_CONNECT_DIST) {
        const alpha = (1 - dist / BG_CONNECT_DIST) * 0.1
        ctx.strokeStyle = `rgba(13,148,136,${alpha})`
        ctx.beginPath()
        ctx.moveTo(bgParticles[i].x, bgParticles[i].y)
        ctx.lineTo(bgParticles[j].x, bgParticles[j].y)
        ctx.stroke()
      }
    }
  }

  // 粒子光晕
  for (const p of bgParticles) {
    const pulse = 1 + Math.sin(time * p.pulse + p.phase) * 0.25
    const r = p.size * pulse
    const [cr, cg, cb] = p.color

    ctx.beginPath()
    ctx.arc(p.x, p.y, r * 2.5, 0, Math.PI * 2)
    ctx.fillStyle = `rgba(${cr},${cg},${cb},${p.opacity * 0.08})`
    ctx.fill()

    ctx.beginPath()
    ctx.arc(p.x, p.y, r, 0, Math.PI * 2)
    ctx.fillStyle = `rgba(${cr},${cg},${cb},${p.opacity * 0.7})`
    ctx.fill()
  }
}

function initBg() {
  const canvas = bgCanvas.value
  if (!canvas) return
  const ctx = canvas.getContext('2d')

  const resize = () => {
    canvas.width = window.innerWidth
    canvas.height = window.innerHeight
    createBgParticles(canvas.width, canvas.height)
  }
  resize()
  window.addEventListener('resize', resize)

  const onMouseMove = (e) => { bgMouse.x = e.clientX; bgMouse.y = e.clientY }
  const onMouseLeave = () => { bgMouse.x = null; bgMouse.y = null }
  document.addEventListener('mousemove', onMouseMove)
  document.addEventListener('mouseleave', onMouseLeave)

  const loop = (time) => {
    animateBg(ctx, canvas.width, canvas.height, time)
    animFrameId = requestAnimationFrame(loop)
  }
  animFrameId = requestAnimationFrame(loop)

  canvas._cleanup = () => {
    cancelAnimationFrame(animFrameId)
    window.removeEventListener('resize', resize)
    document.removeEventListener('mousemove', onMouseMove)
    document.removeEventListener('mouseleave', onMouseLeave)
  }
}
// ── 粒子背景系统结束 ──────────────────────────────────────────────────

// 客服数字人配置
const customerService = {
  name: '小宝',
  title: '金牌客服',
  avatar: createAvatarSvg('宝', 'service'),
  status: '在线'
}

// 用户配置
const userProfile = {
  name: '你',
  avatar: createAvatarSvg('你', 'user')
}

// 数字人头像
const digitalHumanAvatar = createAvatarSvg('数', 'digital')

// ── 数字人（魔珐星云）状态与逻辑 ───────────────────────────────
// 凭证取自设计文档的本地测试 demo；生产环境应改为后端代理下发，避免密钥暴露在前端。
const DIGITAL_HUMAN_APP_ID = '356ede3da317446eb77fea65a9af87f9'
const DIGITAL_HUMAN_APP_SECRET = '588a32f86a35495faf764d6ea8894c50'
const DIGITAL_HUMAN_GATEWAY = 'https://nebula-agent.xingyun3d.com/user/v1/ttsa/session'

const digitalHumanReady = ref(false)
const digitalHumanConnecting = ref(false)
const digitalHumanProgress = ref(0)
const digitalHumanError = ref('')
const digitalHumanStateText = ref('未连接')
let liteSDK = null
let dhInited = false

async function initDigitalHuman() {
  digitalHumanConnecting.value = true
  digitalHumanError.value = ''
  digitalHumanStateText.value = '加载中…'
  digitalHumanProgress.value = 0
  const SDK = window.XmovAvatar
  if (!SDK) {
    digitalHumanConnecting.value = false
    digitalHumanError.value = '数字人 SDK 未加载：请确认 index.html 的脚本引入，以及本机网络能访问 media.xingyun3d.com'
    console.error('[数字人] XmovAvatar 全局未定义')
    return
  }
  // 超时保护：30s 内未完成初始化，给出明确可操作提示（覆盖“静默卡死”场景）
  const dhTimeout = setTimeout(() => {
    if (!digitalHumanReady.value) {
      digitalHumanConnecting.value = false
      digitalHumanStateText.value = '未连接'
      digitalHumanError.value = '初始化超时（30s）：浏览器可能连不上魔珐服务器（公司代理/防火墙拦截），或凭证无效。请按 F12 → Network 看 xingyun3d 请求是 pending 还是 failed。'
      console.error('[数字人] 初始化超时')
    }
  }, 30000)
  try {
    liteSDK = new SDK({
      containerId: '#digital-human-sdk',
      appId: DIGITAL_HUMAN_APP_ID,
      appSecret: DIGITAL_HUMAN_APP_SECRET,
      gatewayServer: DIGITAL_HUMAN_GATEWAY,
      hardwareAcceleration: 'prefer-hardware',
      enableLogger: true,
      onMessage(message) {
        console.log('[数字人] SDK 消息:', message)
        // 50001/50002 为在线/离线模式切换，属正常心跳，不当错误处理
        if (message && message.code && message.code !== 50001 && message.code !== 50002) {
          clearTimeout(dhTimeout)
          digitalHumanConnecting.value = false
          digitalHumanStateText.value = '未连接'
          digitalHumanError.value = `[${message.code}] ${message.message || JSON.stringify(message)}`
          console.error('[数字人] SDK 错误:', message)
        }
      },
      onStateChange(state) { console.log('[数字人] 状态:', state) },
      onStatusChange(status) {
        console.log('[数字人] 连接状态:', status)
        if (typeof status === 'string') digitalHumanStateText.value = '加载中…（' + status + '）'
      },
      onVoiceStateChange(status) {
        if (status === 'start') digitalHumanStateText.value = '正在说话…'
        else if (status === 'end') digitalHumanStateText.value = '已就绪'
      },
    })
    const initPromise = liteSDK.init({
      initModel: 'normal',
      onDownloadProgress(progress) {
        digitalHumanProgress.value = progress
        if (progress >= 100 && !dhInited) {
          dhInited = true
          clearTimeout(dhTimeout)
          digitalHumanReady.value = true
          digitalHumanConnecting.value = false
          digitalHumanStateText.value = '已就绪'
          console.log('[数字人] 资源下载完成，已就绪')
        }
      },
    })
    // 部分 SDK 版本 init 返回 Promise，兜底捕获
    if (initPromise && typeof initPromise.catch === 'function') {
      initPromise.catch((e) => {
        clearTimeout(dhTimeout)
        digitalHumanConnecting.value = false
        digitalHumanStateText.value = '未连接'
        digitalHumanError.value = '初始化失败：' + (e && e.message ? e.message : e)
        console.error('[数字人] init 异常:', e)
      })
    }
  } catch (e) {
    clearTimeout(dhTimeout)
    digitalHumanConnecting.value = false
    digitalHumanError.value = '数字人初始化失败：' + (e && e.message ? e.message : e)
    digitalHumanStateText.value = '未连接'
    console.error('[数字人] 初始化异常:', e)
  }
}

function destroyDigitalHuman() {
  try { if (liteSDK) liteSDK.destroy() } catch (e) { /* 忽略销毁异常 */ }
  liteSDK = null
  dhInited = false
  digitalHumanReady.value = false
  digitalHumanConnecting.value = false
  digitalHumanProgress.value = 0
  digitalHumanStateText.value = '未连接'
}

function toggleDigitalHuman() {
  if (digitalHumanReady.value || digitalHumanConnecting.value) destroyDigitalHuman()
  else initDigitalHuman()
}

function speakDigitalHuman(text) {
  if (!digitalHumanReady.value || !liteSDK || !text) return
  try {
    liteSDK.speak(text, true, true)
  } catch (e) {
    console.error('[数字人] speak 失败:', e)
  }
}

// 将消息分组为 Turn 结构
const turns = computed(() => {
  const result = []
  let currentTurn = null
  let turnIndex = 0

  for (const message of messages.value) {
    if (message.type === 'divider') {
      if (currentTurn) {
        result.push(currentTurn)
        currentTurn = null
      }
      result.push({
        type: 'divider',
        text: message.text
      })
      continue
    }

    if (message.role === 'user') {
      // 如果有待处理的当前 turn，先保存
      if (currentTurn) {
        result.push(currentTurn)
      }
      // 创建新的 turn
      turnIndex++
      currentTurn = {
        type: 'turn',
        id: `turn-${turnIndex}`,
        index: turnIndex,
        userMessage: message,
        botMessages: []
      }
    } else if (message.role === 'bot') {
      if (!currentTurn) {
        // 如果没有当前 turn，创建一个（可能是因为历史消息）
        turnIndex++
        currentTurn = {
          type: 'turn',
          id: `turn-${turnIndex}`,
          index: turnIndex,
          userMessage: null,
          botMessages: []
        }
      }
      currentTurn.botMessages.push(message)
    }
  }

  if (currentTurn) {
    result.push(currentTurn)
  }

  return result
})

const chatEndpoint = computed(() => '/api/chat')
const chatHistoryEndpoint = computed(
  () => `/api/chat/history?sender_id=${encodeURIComponent(senderId.value.trim())}`
)
const commerceOrdersEndpoint = computed(
  () => `/commerce/users/${encodeURIComponent(senderId.value.trim())}/orders`
)
const commerceProductsEndpoint = computed(
  () => `/commerce/users/${encodeURIComponent(senderId.value.trim())}/products`
)

function createBaseMessage(role) {
  return {
    id: crypto.randomUUID(),
    role,
    buttons: [],
  }
}

function appendUserText(text) {
  messages.value.push({
    ...createBaseMessage('user'),
    type: 'text',
    text,
  })
}

function appendUserObject(objectType, payload) {
  messages.value.push({
    ...createBaseMessage('user'),
    type: 'object',
    objectType,
    payload,
  })
}

function appendBotMessages(botMessages) {
  for (const message of botMessages) {
    appendMessage('bot', message)
  }
}

function appendMessage(role, message) {
  if (role === 'divider') {
    messages.value.push({
      ...createBaseMessage('divider'),
      type: 'divider',
      text: message.text ?? '以上为历史消息',
    })
    return
  }

  if (message.object) {
    messages.value.push({
      ...createBaseMessage(role),
      type: 'object',
      objectType: message.object.type,
      payload: message.object,
    })
  } else {
    messages.value.push({
      ...createBaseMessage(role),
      type: 'text',
      text: message.text ?? '',
      suggestions: message.suggestions ?? null,
    })
  }
}

function setHistoryMessages(historyMessages) {
  messages.value = []
  for (const message of historyMessages) {
    const role = ['user', 'bot', 'divider'].includes(message.role) ? message.role : 'bot'
    appendMessage(role, message)
  }
}

async function scrollToBottom() {
  await nextTick()
  const container = messagesContainer.value
  if (!container) {
    return
  }
  container.scrollTop = container.scrollHeight
}

watch(
  () => messages.value.length,
  async () => {
    await scrollToBottom()
  }
)

function resetConversation() {
  messages.value = []
  errorMessage.value = ''
}

function formatAmount(amount) {
  const numericAmount = Number(amount)
  if (Number.isNaN(numericAmount)) {
    return '￥0.00'
  }
  return `￥${numericAmount.toFixed(2)}`
}

function formatOrderSummary(order) {
  return order.status ? `订单状态：${order.status}` : '订单'
}

const ORDER_STATUS_CLASS = {
  '待发货': 'status-warning',
  '待揽收': 'status-warning',
  '运输中': 'status-info',
  '派送中': 'status-info',
  '已完成': 'status-success',
  '已签收': 'status-success',
  '已取消': 'status-muted',
  '退款中': 'status-danger',
  '已退款': 'status-muted',
}

function getStatusClass(status) {
  return ORDER_STATUS_CLASS[status] || 'status-muted'
}

function formatProductSummary(product) {
  if (product.description) {
    return product.description
  }
  if (product.attributes?.price) {
    return `商品价格：${formatAmount(product.attributes.price)}`
  }
  return '商品信息'
}

function getObjectTitle(message) {
  const payload = message.payload ?? {}
  if (payload.title) {
    return payload.title
  }
  return message.objectType === 'order' ? '订单对象' : '商品对象'
}

function getObjectIdentifier(message) {
  const payload = message.payload ?? {}
  const id = payload.order_id ?? payload.product_id ?? payload.id
  const label = message.objectType === 'order' ? '订单号' : '商品号'
  return id ? `${label}：${id}` : label
}

function getObjectSummary(message) {
  const payload = message.payload ?? {}
  if (message.objectType === 'order') {
    const status = payload.status ?? payload.attributes?.status
    return status ? `订单状态：${status}` : '订单'
  }
  return formatProductSummary(payload)
}

function getObjectAmount(message) {
  const payload = message.payload ?? {}
  const amount = message.objectType === 'order'
    ? payload.amount ?? payload.attributes?.amount
    : payload.price ?? payload.attributes?.price
  return formatAmount(amount)
}

async function fetchSidebarData() {
  const currentSenderId = senderId.value.trim()
  orders.value = []
  products.value = []
  sidebarError.value = ''

  if (!currentSenderId) {
    return
  }

  isLoadingSidebar.value = true
  try {
    const [ordersResponse, productsResponse] = await Promise.all([
      fetch(commerceOrdersEndpoint.value),
      fetch(commerceProductsEndpoint.value),
    ])

    const [ordersPayload, productsPayload] = await Promise.all([
      ordersResponse.json(),
      productsResponse.json(),
    ])

    if (!ordersResponse.ok) {
      throw new Error(ordersPayload.detail || '加载订单列表失败。')
    }
    if (!productsResponse.ok) {
      throw new Error(productsPayload.detail || '加载商品列表失败。')
    }

    orders.value = Array.isArray(ordersPayload?.data?.orders) ? ordersPayload.data.orders : []
    products.value = Array.isArray(productsPayload?.data?.products) ? productsPayload.data.products : []
  } catch (error) {
    sidebarError.value = error instanceof Error ? error.message : '加载右侧列表失败。'
  } finally {
    isLoadingSidebar.value = false
  }
}

async function fetchChatHistory() {
  const currentSenderId = senderId.value.trim()
  if (!currentSenderId) {
    messages.value = []
    return
  }

  try {
    const response = await fetch(chatHistoryEndpoint.value)
    const data = await response.json()
    if (!response.ok) {
      throw new Error(data.detail || '加载历史消息失败。')
    }
    if (currentSenderId === senderId.value.trim()) {
      setHistoryMessages(Array.isArray(data?.messages) ? data.messages : [])
    }
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '加载历史消息失败。'
  }
}

async function sendPayload(payload) {
  if (isSending.value) {
    return
  }

  errorMessage.value = ''
  isSending.value = true

  try {
    const response = await fetch(chatEndpoint.value, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        sender_id: senderId.value.trim(),
        ...payload,
      }),
    })

    const data = await response.json()
    if (!response.ok) {
      throw new Error(data.detail || '请求失败。')
    }

    const botMessages = data.messages ?? []
    appendBotMessages(botMessages)
    const speakTexts = botMessages.filter((m) => m && m.text).map((m) => m.text)
    if (speakTexts.length > 0) speakDigitalHuman(speakTexts.join('\n'))
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '请求失败。'
  } finally {
    isSending.value = false
  }
}

async function sendSuggestion(text) {
  appendUserText(text)
  await sendPayload({ text })
}

async function sendQuickText(text) {
  draftMessage.value = text
  await sendTextMessage()
}
async function sendTextMessage() {
  const text = draftMessage.value.trim()
  const currentSenderId = senderId.value.trim()

  if (!currentSenderId) {
    errorMessage.value = '请先输入 sender_id。'
    return
  }
  if (!text) {
    return
  }

  draftMessage.value = ''
  appendUserText(text)
  await sendPayload({ text })
}

async function sendOrder(order) {
  const currentSenderId = senderId.value.trim()
  if (!currentSenderId) {
    errorMessage.value = '请先输入 sender_id。'
    return
  }

  appendUserObject('order', { ...order })
  await sendPayload({
    object: {
      type: 'order',
      id: order.order_id,
      title: order.title,
      attributes: {
        status: order.status,
        amount: order.amount,
        created_at: order.created_at,
        cover_url: order.cover_url,
      },
    },
  })
}

async function sendProduct(product) {
  const currentSenderId = senderId.value.trim()
  if (!currentSenderId) {
    errorMessage.value = '请先输入 sender_id。'
    return
  }

  appendUserObject('product', { ...product })
  await sendPayload({
    object: {
      type: 'product',
      id: product.product_id,
      title: product.title,
      attributes: {
        price: product.price,
        cover_url: product.cover_url,
        description: product.description,
      },
    },
  })
}

watch(
  () => senderId.value.trim(),
  async (value, previousValue) => {
    if (value === previousValue) {
      return
    }

    resetConversation()
    if (!value) {
      orders.value = []
      products.value = []
      return
    }
    await Promise.all([fetchSidebarData(), fetchChatHistory()])
  }
)

onMounted(async () => {
  // 未登录 / 已退出登录 → 回到登录页
  if (!getSession()) {
    window.location.replace('/login')
    return
  }
  initBg()
  await Promise.all([fetchSidebarData(), fetchChatHistory()])
})

onUnmounted(() => {
  if (bgCanvas.value?._cleanup) bgCanvas.value._cleanup()
  destroyDigitalHuman()
})

async function playTts(botMsg) {
  const msgId = botMsg.id
  if (!botMsg.text || ttsState.value[msgId] === 'loading') return

  if (currentAudio) { currentAudio.pause(); currentAudio = null }
  for (const key of Object.keys(ttsState.value)) {
    if (ttsState.value[key] === 'playing') ttsState.value[key] = 'idle'
  }

  ttsState.value[msgId] = 'loading'
  try {
    const response = await fetch('/api/chat/tts', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text: botMsg.text }),
    })
    if (!response.ok) throw new Error('TTS 请求失败')
    const blob = await response.blob()
    const url = URL.createObjectURL(blob)
    currentAudio = new Audio(url)
    ttsState.value[msgId] = 'playing'
    currentAudio.onended = () => { ttsState.value[msgId] = 'idle'; URL.revokeObjectURL(url); currentAudio = null }
    currentAudio.onerror = () => { ttsState.value[msgId] = 'idle'; URL.revokeObjectURL(url); currentAudio = null }
    await currentAudio.play()
  } catch (error) {
    ttsState.value[msgId] = 'idle'
    console.error('TTS error:', error)
  }
}

async function copyBotText(botMsg) {
  const msgId = botMsg.id
  try {
    await navigator.clipboard.writeText(botMsg.text)
    copyState.value[msgId] = true
    setTimeout(() => { copyState.value[msgId] = false }, 1800)
  } catch (error) {
    console.error('Copy failed:', error)
  }
}
</script>

<template>
  <div class="app-shell">
    <canvas ref="bgCanvas" class="bg-canvas"></canvas>
      <div class="workspace">
        <aside class="digital-human">
          <div class="dh-header">
            <div :class="{ online: digitalHumanReady }" class="dh-avatar">
              <img :src="digitalHumanAvatar" alt="数" class="dh-avatar-img" />
              <span class="dh-status-dot"></span>
            </div>
            <div class="dh-meta">
              <span class="dh-name">数字人 · 小宝</span>
              <span class="dh-state">{{ digitalHumanStateText }}</span>
            </div>
          </div>
          <div class="dh-stage">
            <div id="digital-human-sdk"></div>
            <div v-if="!digitalHumanReady && !digitalHumanConnecting" class="dh-placeholder">
              <span class="dh-placeholder-icon">🎭</span>
              <span>点击「连接数字人」<br />加载 3D 形象</span>
            </div>
          </div>
          <div v-if="digitalHumanConnecting" class="dh-progress">
            <div :style="{ width: digitalHumanProgress + '%' }" class="dh-progress-bar"></div>
          </div>
          <button
            :class="{ danger: digitalHumanReady }"
            :disabled="digitalHumanConnecting"
            class="dh-button"
            type="button"
            @click="toggleDigitalHuman"
          >
            {{ digitalHumanReady ? '断开数字人' : (digitalHumanConnecting ? '连接中…' : '连接数字人') }}
          </button>
          <p v-if="digitalHumanError" class="dh-error">{{ digitalHumanError }}</p>
        </aside>
        <div class="chat-card">
        <header class="chat-header">
          <div class="header-content">
            <div class="header-info">
              <h1>电商客服系统</h1>
                <div class="service-info">
                  <div class="service-avatar-wrapper">
                    <img :src="customerService.avatar" alt="小宝" class="service-avatar" />
                    <span class="status-indicator"></span>
                  </div>
                  <div class="service-details">
                  <span class="service-name">{{ customerService.name }}</span>
                  <span class="service-status">{{ customerService.status }}</span>
                </div>
              </div>
            </div>
            <div class="header-actions">
              <button class="clear-button" title="清空对话" type="button" @click="resetConversation">
                <span>🔄</span>
                <span>新对话</span>
              </button>

              <div class="user-menu">
                <div class="user-chip">
                  <span class="user-avatar">{{ userInitial }}</span>
                  <span class="user-meta">
                    <span class="user-name">{{ sessionName }}</span>
                    <span v-if="sessionAccount" class="user-account">{{ sessionAccount }}</span>
                  </span>
                </div>
                <button
                  :disabled="loggingOut"
                  class="logout-button"
                  title="退出登录"
                  type="button"
                  @click="handleLogout"
                >
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"
                       stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                    <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
                    <path d="M16 17l5-5-5-5" />
                    <path d="M21 12H9" />
                  </svg>
                  <span>退出登录</span>
                </button>
              </div>
            </div>
          </div>
        </header>

        <section class="controls">
          <label class="field">
            <span>sender_id</span>
            <div class="field-row">
              <input v-model="senderId" placeholder="u1001" type="text" />
              <button
                :disabled="isLoadingSidebar"
                class="secondary-button"
                type="button"
                @click="fetchSidebarData"
              >
                {{ isLoadingSidebar ? '加载中...' : '刷新对象列表' }}
              </button>
            </div>
          </label>
        </section>

        <section ref="messagesContainer" class="messages">
          <div v-if="turns.length === 0" class="welcome">
            <div class="welcome-card">
              <div class="welcome-glow"></div>
              <div class="welcome-avatar-wrapper">
                <img :src="customerService.avatar" alt="小宝" class="welcome-avatar" />
              </div>
              <h2 class="welcome-greeting">Hi，我是 {{ customerService.name }}</h2>
              <p class="welcome-subtitle">你的专属电商客服，随时为你服务</p>
              <div class="welcome-chips">
                <button
                  v-for="chip in ['我要退款', '查订单状态', '商品推荐', '退换货政策']"
                  :key="chip"
                  :disabled="isSending"
                  class="welcome-chip"
                  type="button"
                  @click="sendQuickText(chip)"
                >{{ chip }}</button>
              </div>
              <p class="welcome-features">
                <span>💬 文字对话</span>
                <span>🔊 语音播报</span>
                <span>📦 订单查询</span>
                <span>🛍️ 商品咨询</span>
              </p>
            </div>
          </div>

          <!-- Turn 结构展示 -->
          <template v-for="(item, index) in turns" :key="item.id || index">
            <!-- 分隔线 -->
            <div v-if="item.type === 'divider'" class="history-divider">
              <span>{{ item.text }}</span>
            </div>

            <!-- Turn 卡片 -->
            <div v-else :class="{ 'has-user-message': item.userMessage }" class="turn-card">
              <!-- Turn 标识 -->
              <div class="turn-header">
                <span class="turn-badge">Turn {{ item.index }}</span>
                <span class="turn-label">对话轮次</span>
              </div>

              <!-- 用户消息区域 -->
              <div v-if="item.userMessage" class="turn-section user-section">
                <div class="section-header">
                  <div class="avatar-wrapper user-avatar">
                    <img :src="userProfile.avatar" alt="你" class="avatar" />
                  </div>
                  <div class="agent-info">
                    <span class="agent-name">{{ userProfile.name }}</span>
                    <span class="agent-label">用户</span>
                  </div>
                </div>
                <div class="turn-bubble user-bubble">
                  <template v-if="item.userMessage.type === 'object'">
                    <div :class="`object-card-${item.userMessage.objectType}`" class="object-card">
                      <div class="object-card-badge">
                        {{ item.userMessage.objectType === 'order' ? '订单对象' : '商品对象' }}
                      </div>
                      <img
                        v-if="item.userMessage.type === 'object' && item.userMessage.payload.cover_url"
                        :alt="getObjectTitle(item.userMessage)"
                        :src="item.userMessage.payload.cover_url"
                        class="object-card-image"
                        @error="$event.target.style.display='none'"
                      />
                      <div class="object-card-title">{{ getObjectTitle(item.userMessage) }}</div>
                      <div class="object-card-meta">{{ getObjectIdentifier(item.userMessage) }}</div>
                      <div class="object-card-meta">
                        <span v-if="item.userMessage.objectType === 'order' && item.userMessage.payload.status" :class="getStatusClass(item.userMessage.payload.status)" class="status-badge">{{ item.userMessage.payload.status }}</span>
                        <span v-else>{{ getObjectSummary(item.userMessage) }}</span>
                      </div>
                      <div class="object-card-price">{{ getObjectAmount(item.userMessage) }}</div>
                    </div>
                  </template>
                  <template v-else>
                    <p>{{ item.userMessage.text }}</p>
                  </template>
                </div>
              </div>

              <!-- 客服回复区域 -->
              <div v-if="item.botMessages.length > 0" class="turn-section bot-section">
                <div class="section-header">
                  <div class="avatar-wrapper service-avatar">
                    <img :src="customerService.avatar" alt="小宝" class="avatar" />
                    <span class="status-dot"></span>
                  </div>
                  <div class="agent-info">
                    <span class="agent-name">{{ customerService.name }}</span>
                    <span class="agent-label">{{ customerService.title }}</span>
                  </div>
                </div>
                <div class="bot-messages">
                  <div
                    v-for="(botMsg, msgIndex) in item.botMessages"
                    :key="msgIndex"
                    class="turn-bubble bot-bubble"
                  >
                    <template v-if="botMsg.type === 'object'">
                      <div :class="`object-card-${botMsg.objectType}`" class="object-card">
                        <div class="object-card-badge">
                          {{ botMsg.objectType === 'order' ? '订单对象' : '商品对象' }}
                        </div>
                        <img
                          v-if="botMsg.type === 'object' && botMsg.payload.cover_url"
                          :alt="getObjectTitle(botMsg)"
                          :src="botMsg.payload.cover_url"
                          class="object-card-image"
                          @error="$event.target.style.display='none'"
                        />
                        <div class="object-card-title">{{ getObjectTitle(botMsg) }}</div>
                        <div class="object-card-meta">{{ getObjectIdentifier(botMsg) }}</div>
                        <div class="object-card-meta">
                          <span v-if="botMsg.objectType === 'order' && botMsg.payload.status" :class="getStatusClass(botMsg.payload.status)" class="status-badge">{{ botMsg.payload.status }}</span>
                          <span v-else>{{ getObjectSummary(botMsg) }}</span>
                        </div>
                        <div class="object-card-price">{{ getObjectAmount(botMsg) }}</div>
                      </div>
                    </template>
                    <template v-else>
                      <div class="bot-text-row">
                        <p>{{ botMsg.text }}</p>
                        <div class="bot-actions">
                          <button :class="{ 'tts-loading': ttsState[botMsg.id] === 'loading', 'tts-playing': ttsState[botMsg.id] === 'playing' }" :disabled="ttsState[botMsg.id] === 'loading'"
                            :title="ttsState[botMsg.id] === 'playing' ? '正在播放...' : '语音播报'"
                            class="tts-button"
                            type="button"
                            @click.stop="playTts(botMsg)">
                            <span v-if="ttsState[botMsg.id] === 'loading'" class="tts-spinner"></span>
                            <span v-else-if="ttsState[botMsg.id] === 'playing'" class="tts-bars">
                              <span></span><span></span><span></span>
                            </span>
                            <span v-else>🔈</span>
                          </button>
                          <button :class="{ 'copy-done': copyState[botMsg.id] }" :title="copyState[botMsg.id] ? '已复制' : '复制文字'"
                            class="copy-button"
                            type="button"
                            @click.stop="copyBotText(botMsg)">
                            <span v-if="copyState[botMsg.id]">✓</span>
                            <span v-else>📋</span>
                          </button>
                        </div>
                      </div>
                    </template>
                    <div v-if="botMsg.suggestions && botMsg.suggestions.length > 0" class="suggestion-chips">
                      <button
                        v-for="sug in botMsg.suggestions"
                        :key="sug"
                        :disabled="isSending"
                        class="suggestion-chip"
                        type="button"
                        @click.stop="sendSuggestion(sug)"
                      >{{ sug }}</button>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </template>
        </section>

        <div v-if="isSending" class="typing-indicator">
          <div class="typing-avatar">
            <img :src="customerService.avatar" alt="小宝" class="typing-avatar-img" />
          </div>
          <div class="typing-bubble">
            <span class="typing-dots">
              <span></span><span></span><span></span>
            </span>
            <span class="typing-label">小宝正在输入...</span>
          </div>
        </div>

        <p v-if="errorMessage" class="error-message">
          {{ errorMessage }}
        </p>

        <form class="composer" @submit.prevent="sendTextMessage">
          <input
            v-model="draftMessage"
            :disabled="isSending"
            placeholder="请输入咨询内容..."
            type="text"
          />
          <button :disabled="isSending || !draftMessage.trim()" type="submit">
            {{ isSending ? '发送中...' : '发送' }}
          </button>
        </form>
      </div>

      <aside class="sidebar">
        <div class="sidebar-header">
          <h2>业务对象</h2>
        </div>

        <div class="tabs">
          <button
            :class="{ active: activeTab === 'orders' }"
            class="tab-button"
            type="button"
            @click="activeTab = 'orders'"
          >
            订单
          </button>
          <button
            :class="{ active: activeTab === 'products' }"
            class="tab-button"
            type="button"
            @click="activeTab = 'products'"
          >
            商品
          </button>
        </div>

        <p v-if="sidebarError" class="sidebar-error">{{ sidebarError }}</p>

        <div v-if="activeTab === 'orders'" class="sidebar-list">
          <div v-if="!orders.length && !isLoadingSidebar" class="sidebar-empty">
            暂无订单数据
          </div>

          <article v-for="order in orders" :key="order.order_id" class="sidebar-card">
            <div class="card-image-wrapper">
              <img
                v-if="order.cover_url"
                :alt="order.title"
                :src="order.cover_url"
                class="card-image"
                @error="$event.target.style.display='none'"
              />
              <div v-else class="card-image-placeholder">📦</div>
            </div>
            <div class="card-top">
              <div class="card-title">{{ order.title }}</div>
              <div class="card-amount">{{ formatAmount(order.amount) }}</div>
            </div>
            <div class="card-meta">订单号：{{ order.order_id }}</div>
            <div class="card-meta">
              <span :class="getStatusClass(order.status)" class="status-badge">{{ order.status }}</span>
            </div>
            <button
              :disabled="isSending"
              class="secondary-button full-width"
              type="button"
              @click="sendOrder(order)"
            >
              发送订单
            </button>
          </article>
        </div>

        <div v-else class="sidebar-list">
          <div v-if="!products.length && !isLoadingSidebar" class="sidebar-empty">
            暂无商品数据
          </div>

          <article v-for="product in products" :key="product.product_id" class="sidebar-card">
            <div class="card-image-wrapper">
              <img
                v-if="product.cover_url"
                :alt="product.title"
                :src="product.cover_url"
                class="card-image"
                @error="$event.target.style.display='none'"
              />
              <div v-else class="card-image-placeholder">🛍️</div>
            </div>
            <div class="card-top">
              <div class="card-title">{{ product.title }}</div>
              <div class="card-amount">{{ formatAmount(product.price) }}</div>
            </div>
            <div class="card-meta">商品号：{{ product.product_id }}</div>
            <div class="card-meta">商品信息：最近浏览 / 购买商品</div>
            <button
              :disabled="isSending"
              class="secondary-button full-width"
              type="button"
              @click="sendProduct(product)"
            >
              发送商品
            </button>
          </article>
        </div>
      </aside>
    </div>
  </div>
</template>

<style scoped>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300..700&family=Zen+Maru+Gothic:wght@400;500;700&display=swap');

:global(*) {
  box-sizing: border-box;
}

:global(:root) {
  /* ── Palette (Apple light) ── */
  --color-bg-deep: #f5f5f7;
  --color-bg-mid: #f5f5f7;
  --color-bg-surface: #f5f5f7;
  /* Clean white surfaces, no frosted glass */
  --color-surface: #ffffff;
  --color-surface-hover: #fbfbfd;
  --color-surface-dim: #f5f5f7;
  --color-surface-raised: #fbfbfd;
  --color-surface-field: #f5f5f7;
  /* Near-black text on light surfaces */
  --color-text-primary: #1d1d1f;
  --color-text-secondary: #6e6e73;
  --color-text-muted: #86868b;
  --color-text-inverse: #f5f5f7;
  /* Accent — Apple blue */
  --color-accent: #0071e3;
  --color-accent-strong: #0077ed;
  --color-accent-soft: rgba(0, 113, 227, 0.10);
  --color-accent-glow: rgba(0, 113, 227, 0.12);
  --color-accent-soft-bg: rgba(0, 113, 227, 0.06);
  /* WeChat-style user bubble green */
  --color-wechat-green: #95ec69;
  --color-wechat-green-strong: #7bd960;
  --color-wechat-green-text: #1a1a1a;
  /* Warm — amber (kept for order status) */
  --color-warm: #f59e0b;
  --color-warm-strong: #b25000;
  --color-warm-soft: rgba(245, 158, 11, 0.10);
  --color-warm-glow: rgba(245, 158, 11, 0.08);
  --color-warm-soft-bg: rgba(245, 158, 11, 0.05);
  /* Semantic */
  --color-success: #34c759;
  --color-success-soft: rgba(52, 199, 89, 0.12);
  --color-info: #0071e3;
  --color-info-soft: rgba(0, 113, 227, 0.10);
  --color-danger: #ff3b30;
  --color-danger-soft: rgba(255, 59, 48, 0.10);
  /* Borders — subtle hairlines on light */
  --color-border: rgba(0, 0, 0, 0.10);
  --color-border-light: rgba(0, 0, 0, 0.06);
  --color-border-strong: rgba(0, 0, 0, 0.15);
  /* ── Radii ── */
  --radius-sm: 10px;
  --radius-md: 14px;
  --radius-lg: 20px;
  --radius-xl: 24px;
  --radius-full: 9999px;
  /* ── Shadows (soft, light theme) ── */
  --shadow-xs: 0 1px 2px rgba(0, 0, 0, 0.05);
  --shadow-sm: 0 2px 8px rgba(0, 0, 0, 0.06);
  --shadow-md: 0 6px 20px rgba(0, 0, 0, 0.08);
  --shadow-lg: 0 12px 40px rgba(0, 0, 0, 0.10);
  --shadow-glow-teal: 0 0 0 rgba(0, 0, 0, 0);
  --shadow-glow-amber: 0 0 0 rgba(0, 0, 0, 0);
  --shadow-inner-glow: inset 0 1px 0 rgba(255, 255, 255, 0.6);
  /* ── Transitions ── */
  --ease-out-expo: cubic-bezier(0.16, 1, 0.3, 1);
  --ease-out-back: cubic-bezier(0.34, 1.56, 0.64, 1);
  --ease-in-out: cubic-bezier(0.65, 0, 0.35, 1);
  --duration-fast: 150ms;
  --duration-base: 250ms;
  --duration-slow: 400ms;
}

:global(body) {
  margin: 0;
  font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", "SF Pro Text", "PingFang SC", "Microsoft YaHei", sans-serif;
  background: var(--color-bg-deep);
  color: var(--color-text-primary);
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

:global(button),
:global(input) {
  font: inherit;
}

:global(#app) {
  min-height: 100vh;
}

.app-shell {
  min-height: 100vh;
  padding: 24px;
  position: relative;
  overflow: hidden;
  background: #f5f5f7;
}
/* Subtle grain texture overlay */
.app-shell::before {
  display: none;
}

.bg-canvas {
  position: absolute;
  inset: 0;
  z-index: 0;
  pointer-events: none;
}

.app-shell::after {
  display: none;
}
/* Teal orb — top left */
.app-shell::after {
  width: 820px; height: 820px;
  background: radial-gradient(circle, rgba(13, 148, 136, 0.18) 0%, rgba(20, 184, 166, 0.06) 35%, transparent 70%);
  top: -320px; left: -280px;
  animation: orb1 20s ease-in-out infinite;
}
/* Amber orb — bottom right */
.workspace::before {
  display: none;
}

@keyframes bgShift {
  0%, 100% { background-position: 0% 0%; }
  25% { background-position: 100% 0%; }
  50% { background-position: 100% 100%; }
  75% { background-position: 0% 100%; }
}
@keyframes orb1 {
  0%, 100% { transform: translate(0, 0) scale(1); }
  33% { transform: translate(140px, 90px) scale(1.22); }
  66% { transform: translate(-50px, 150px) scale(0.82); }
}
@keyframes orb2 {
  0%, 100% { transform: translate(0, 0) scale(1); }
  33% { transform: translate(-110px, -70px) scale(1.18); }
  66% { transform: translate(70px, -130px) scale(0.88); }
}

.workspace {
  width: min(1760px, 100%);
  margin: 0 auto;
  display: grid;
  grid-template-columns: 360px minmax(0, 1fr) 370px;
  gap: 22px;
  position: relative;
  z-index: 1;
}

.chat-card,
.sidebar {
  min-height: calc(100vh - 48px);
  height: calc(100vh - 48px);
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  overflow: hidden;
  transition: border-color var(--duration-slow) var(--ease-in-out), box-shadow var(--duration-slow) var(--ease-in-out);
}
.chat-card {
  display: flex;
  flex-direction: column;
  box-shadow: var(--shadow-lg);
}
.chat-card:hover {
  border-color: rgba(0, 113, 227, 0.25);
}
.sidebar {
  display: flex;
  flex-direction: column;
  box-shadow: var(--shadow-lg);
}
.sidebar:hover {
  border-color: rgba(0, 113, 227, 0.25);
}

.chat-header,
.sidebar-header {
  padding: 24px 24px 16px;
  border-bottom: 1px solid var(--color-border-light);
}

.chat-header {
  display: flex;
  justify-content: space-between;
  gap: 20px;
  align-items: center;
}

.header-content {
  display: flex;
  align-items: center;
  gap: 16px;
  width: 100%;
}

.header-info {
  display: flex;
  flex-direction: column;
  gap: 8px;
  flex: 1;
}

.chat-header h1,
.sidebar-header h2 {
  margin: 0;
  font-size: 24px;
  line-height: 1.2;
  letter-spacing: -0.02em;
  color: var(--color-text-primary);
}

.sidebar-header h2 {
  font-size: 22px;
  color: var(--color-text-primary);
}

.chat-header p,
.sidebar-header p {
  margin: 10px 0 0;
  color: var(--color-text-secondary);
}

/* 客服信息 */
.service-info {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 16px;
  background: var(--color-surface-raised);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
}

.service-avatar-wrapper {
  position: relative;
  flex-shrink: 0;
  width: 48px;
  height: 48px;
  border-radius: 50%;
  overflow: hidden;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}

.service-avatar {
  width: 100%;
  height: 100%;
  border-radius: 50%;
  object-fit: cover;
  display: block;
}

.status-indicator {
  position: absolute;
  bottom: 2px;
  right: 2px;
  width: 12px;
  height: 12px;
  background: var(--color-success);
  border: 2px solid #f5f5f7;
  border-radius: 50%;
  z-index: 1;
}

.service-details {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.service-name {
  font-size: 15px;
  font-weight: 600;
  color: var(--color-text-primary);
}

.service-status {
  font-size: 12px;
  color: var(--color-success);
  font-weight: 500;
  display: flex;
  align-items: center;
  gap: 4px;
}

.service-status::before {
  content: '';
  width: 6px;
  height: 6px;
  background: var(--color-success);
  border-radius: 50%;
}

.clear-button {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-surface-raised);
  color: var(--color-text-secondary);
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all var(--duration-base) var(--ease-out-expo);
  white-space: nowrap;
}
.clear-button:hover {
  background: rgba(251, 113, 133, 0.10);
  border-color: var(--color-danger);
  color: var(--color-danger);
  transform: translateY(-1px);
  box-shadow: 0 4px 18px var(--color-danger-soft);
}

/* ── 头部右侧：操作区（新对话 + 用户信息 + 退出登录） ───────────── */
.header-actions {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
}

.user-menu {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 4px 4px 6px;
  background: var(--color-surface-raised);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
}

.user-chip {
  display: flex;
  align-items: center;
  gap: 8px;
  padding-right: 6px;
  min-width: 0;
}

.user-avatar {
  flex-shrink: 0;
  width: 30px;
  height: 30px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  background: linear-gradient(135deg, #3aa0ff, #0071e3);
  color: #ffffff;
  font-size: 14px;
  font-weight: 600;
  line-height: 1;
}

.user-meta {
  display: flex;
  flex-direction: column;
  gap: 1px;
  min-width: 0;
  max-width: 150px;
}

.user-name {
  font-size: 13px;
  font-weight: 600;
  color: var(--color-text-primary);
  line-height: 1.2;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.user-account {
  font-size: 11px;
  color: var(--color-text-muted);
  line-height: 1.2;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.logout-button {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  min-height: 32px;
  padding: 6px 12px;
  border: 1px solid transparent;
  border-radius: calc(var(--radius-md) - 4px);
  background: transparent;
  color: var(--color-text-secondary);
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  white-space: nowrap;
  transition: all var(--duration-base) var(--ease-out-expo);
}

.logout-button svg {
  width: 15px;
  height: 15px;
  flex-shrink: 0;
}

.logout-button:hover:not(:disabled) {
  background: rgba(255, 59, 48, 0.09);
  border-color: rgba(255, 59, 48, 0.28);
  color: var(--color-danger);
}

.logout-button:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.controls {
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  gap: 12px;
  padding: 20px 24px;
  border-bottom: 1px solid var(--color-border-light);
}

.field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.field span {
  color: var(--color-text-secondary);
  font-size: 13px;
  font-weight: 500;
}

.field-row {
  display: flex;
  gap: 12px;
}

.field input,
.composer input {
  width: 100%;
  min-width: 0;
  min-height: 46px;
  padding: 11px 14px;
  border: 1px solid var(--color-border-strong);
  border-radius: var(--radius-md);
  background: var(--color-surface-field);
  color: var(--color-text-primary);
  font-size: 15px;
  line-height: 1.4;
  transition: border-color var(--duration-fast) var(--ease-in-out), box-shadow var(--duration-fast) var(--ease-in-out);
}
.field input::placeholder,
.composer input::placeholder {
  color: var(--color-text-muted);
}
.field input:focus,
.composer input:focus {
  outline: none;
  border-color: var(--color-accent);
  box-shadow: 0 0 0 3px var(--color-accent-soft);
}

.messages {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  scrollbar-gutter: stable;
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

/* Turn 卡片样式 —— 微信风：去掉卡片背景，消息按左右气泡排列 */
.turn-card {
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  gap: 18px;
  padding: 12px 0;
  background: transparent;
  border: none;
  border-radius: 0;
  position: relative;
  overflow: visible;
  animation: msgEnter 0.35s var(--ease-out-expo) both;
}
@keyframes msgEnter {
  from { opacity: 0; transform: translateY(12px); }
  to { opacity: 1; transform: translateY(0); }
}
.turn-card::before {
  display: none;
}

.turn-header {
  display: none;
}

.turn-badge,
.turn-label {
  display: none;
}

.turn-section {
  display: flex;
  flex-direction: row;
  align-items: flex-start;
  gap: 10px;
  max-width: 100%;
}

.user-section {
  flex-direction: row-reverse;
  justify-content: flex-start;
}

.bot-section {
  flex-direction: row;
  justify-content: flex-start;
}

.section-header {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  width: 42px;
  flex-shrink: 0;
}

.agent-info {
  align-items: center;
  gap: 2px;
}

.agent-name {
  font-size: 11px;
  color: var(--color-text-muted);
  font-weight: 500;
}

.agent-label {
  display: none;
}

.user-section .agent-name {
  color: var(--color-text-muted);
}

.bot-section .agent-name {
  color: var(--color-text-muted);
}

/* 头像样式 —— 卡通文字头像（SVG） */
.avatar-wrapper {
  position: relative;
  flex-shrink: 0;
  width: 42px;
  height: 42px;
  border-radius: 50%;
  overflow: hidden;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}

.avatar-wrapper .avatar {
  width: 100%;
  height: 100%;
  border-radius: 50%;
  object-fit: cover;
  display: block;
}

.status-dot {
  position: absolute;
  bottom: 2px;
  right: 2px;
  width: 10px;
  height: 10px;
  background: var(--color-success);
  border: 2px solid #ffffff;
  border-radius: 50%;
}

@keyframes pulse {
  0%, 100% {
    opacity: 1;
    transform: scale(1);
  }
  50% {
    opacity: 0.65;
    transform: scale(1.12);
  }
}

.agent-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.agent-name {
  font-size: 15px;
  font-weight: 600;
  color: var(--color-text-primary);
}

.agent-label {
  font-size: 12px;
  color: var(--color-text-muted);
  font-weight: 500;
}

.user-section .agent-name {
  color: var(--color-info);
}

.bot-section .agent-name {
  color: var(--color-success);
}

.role-icon {
  font-size: 16px;
}

.role-label {
  color: var(--color-text-secondary);
}

.user-section .role-label {
  color: var(--color-info);
}

.bot-section .role-label {
  color: var(--color-success);
}

.turn-bubble {
  padding: 10px 14px;
  border-radius: 18px;
  max-width: 70%;
  font-size: 15px;
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-word;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
}

.user-bubble {
  background: var(--color-wechat-green);
  border: 1px solid transparent;
  color: var(--color-wechat-green-text);
  border-radius: 18px 4px 18px 18px;
}

.bot-bubble {
  background: #ffffff;
  border: 1px solid rgba(0, 0, 0, 0.06);
  color: var(--color-text-primary);
  border-radius: 4px 18px 18px 18px;
}

.bot-messages {
  display: flex;
  flex-direction: column;
  gap: 10px;
  flex: 1;
  min-width: 0;
}

.turn-bubble p {
  margin: 0;
  font-size: 15px;
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-word;
}

.user-bubble p {
  color: var(--color-wechat-green-text);
}

/* 历史消息分隔线 */
.history-divider {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  gap: 14px;
  color: var(--color-text-muted);
  font-size: 13px;
  padding: 8px 0;
}

.history-divider::before,
.history-divider::after {
  content: "";
  flex: 1;
  height: 1px;
  background: var(--color-border-strong);
}

.history-divider span {
  padding: 6px 14px;
  border-radius: var(--radius-full);
  background: var(--color-surface-raised);
  border: 1px solid var(--color-border);
  font-size: 12px;
}

.welcome {
  flex-shrink: 0;
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
}
.welcome-card {
  position: relative;
  max-width: 480px;
  width: 100%;
  padding: 44px 40px;
  background: var(--color-surface-raised);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  text-align: center;
  box-shadow: var(--shadow-lg);
  overflow: hidden;
  animation: welcomeFloat 0.6s var(--ease-out-back);
}
@keyframes welcomeFloat {
  from { opacity: 0; transform: translateY(36px) scale(0.94); }
  to { opacity: 1; transform: translateY(0) scale(1); }
}
.welcome-glow {
  display: none;
}
.welcome-avatar-wrapper {
  position: relative;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 88px;
  height: 88px;
  border-radius: 50%;
  margin-bottom: 20px;
  overflow: hidden;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.08);
}
.welcome-avatar {
  width: 100%;
  height: 100%;
  border-radius: 50%;
  object-fit: cover;
  display: block;
}
.welcome-greeting {
  margin: 0 0 8px;
  font-size: 26px;
  font-weight: 600;
  color: var(--color-text-primary);
  letter-spacing: -0.02em;
}
.welcome-subtitle {
  margin: 0 0 28px;
  color: var(--color-text-secondary);
  font-size: 15px;
}
.welcome-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  justify-content: center;
  margin-bottom: 28px;
}
.welcome-chip {
  padding: 10px 20px;
  border: 1px solid rgba(0, 0, 0, 0.08);
  border-radius: var(--radius-full);
  background: #f5f5f7;
  color: var(--color-text-primary);
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all var(--duration-base) var(--ease-out-expo);
}
.welcome-chip:hover:not(:disabled) {
  background: #e5e5ea;
  border-color: rgba(0, 0, 0, 0.12);
  transform: translateY(-2px);
}
.welcome-chip:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}
.welcome-features {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  justify-content: center;
  margin: 0;
  color: var(--color-text-muted);
  font-size: 13px;
}

.sidebar-empty {
  margin: auto;
  max-width: 420px;
  color: var(--color-text-muted);
  text-align: center;
  line-height: 1.7;
}

.typing-indicator {
  flex-shrink: 0;
  display: flex;
  align-items: flex-end;
  gap: 10px;
  padding: 0 20px;
  animation: msgEnter 0.3s var(--ease-out-expo);
}
.typing-avatar {
  position: relative;
  width: 34px;
  height: 34px;
  border-radius: 50%;
  overflow: hidden;
  flex-shrink: 0;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.06);
}
.typing-avatar-img {
  width: 100%;
  height: 100%;
  border-radius: 50%;
  object-fit: cover;
  display: block;
}
.typing-bubble {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 18px;
  background: var(--color-surface-raised);
  border: 1px solid var(--color-border);
  border-radius: 20px 20px 20px 6px;
  box-shadow: var(--shadow-sm);
}
.typing-dots {
  display: flex;
  gap: 4px;
  align-items: center;
}
.typing-dots span {
  width: 8px; height: 8px;
  border-radius: 50%;
  background: var(--color-accent);
  animation: dotBounce 1.2s ease-in-out infinite;
}
.typing-dots span:nth-child(1) { animation-delay: 0s; }
.typing-dots span:nth-child(2) { animation-delay: 0.2s; }
.typing-dots span:nth-child(3) { animation-delay: 0.4s; }
@keyframes dotBounce {
  0%, 60%, 100% { transform: translateY(0); opacity: 0.3; }
  30% { transform: translateY(-8px); opacity: 1; }
}
.typing-label {
  font-size: 13px;
  color: var(--color-text-muted);
}

.object-card-price {
  font-size: 15px;
  font-weight: 600;
  color: var(--color-text-primary);
}

/* ── 状态徽章 ────────────────────────────────────────────── */
.status-badge {
  display: inline-flex;
  align-items: center;
  padding: 3px 12px;
  border-radius: var(--radius-full);
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.02em;
}
.status-warning {
  background: var(--color-warm-soft);
  color: var(--color-warm-strong);
  border: 1px solid rgba(245, 158, 11, 0.25);
}
.status-info {
  background: var(--color-info-soft);
  color: var(--color-info);
  border: 1px solid rgba(56, 189, 248, 0.25);
}
.status-success {
  background: var(--color-success-soft);
  color: var(--color-success);
  border: 1px solid rgba(52, 211, 153, 0.25);
}
.status-muted {
  background: rgba(113, 111, 104, 0.12);
  color: var(--color-text-muted);
  border: 1px solid rgba(113, 111, 104, 0.18);
}
.status-danger {
  background: var(--color-danger-soft);
  color: var(--color-danger);
  border: 1px solid rgba(251, 113, 133, 0.25);
}

/* ── 商品图片（侧边栏） ────────────────────────────────────── */
.card-image-wrapper {
  width: 100%;
  height: 140px;
  border-radius: var(--radius-sm);
  overflow: hidden;
  background: var(--color-surface-field);
  border: 1px solid var(--color-border-light);
  display: flex;
  align-items: center;
  justify-content: center;
}
.card-image {
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: transform var(--duration-base) var(--ease-out-expo);
}
.sidebar-card:hover .card-image {
  transform: scale(1.05);
}
.card-image-placeholder {
  font-size: 40px;
  opacity: 0.5;
}

/* ── 对象卡片图片（聊天区） ─────────────────────────────────── */
.object-card-image {
  width: 100%;
  height: 150px;
  object-fit: cover;
  border-radius: var(--radius-sm);
  margin-bottom: 8px;
  border: 1px solid var(--color-border-light);
  background: var(--color-surface-field);
}

/* Turn 卡片中的对象卡片样式调整 */
.turn-bubble .object-card {
  min-width: 200px;
}

.user-bubble .object-card-badge {
  background: rgba(255, 255, 255, 0.2);
  color: #ffffff;
}

.composer button,
.secondary-button,
.tab-button {
  min-height: 42px;
  padding: 9px 16px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-surface);
  color: var(--color-text-primary);
  cursor: pointer;
  font-size: 14px;
  font-weight: 600;
  line-height: 1.2;
  transition:
    transform var(--duration-fast) var(--ease-out-expo),
    box-shadow var(--duration-fast) var(--ease-out-expo),
    background var(--duration-fast) var(--ease-in-out),
    border-color var(--duration-fast) var(--ease-in-out);
}

.composer button:hover:not(:disabled),
.secondary-button:hover:not(:disabled),
.tab-button:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: var(--shadow-sm);
}

.composer button:active:not(:disabled),
.secondary-button:active:not(:disabled),
.tab-button:active:not(:disabled) {
  transform: translateY(0);
}

.composer button:disabled,
.secondary-button:disabled {
  opacity: 0.55;
  cursor: not-allowed;
  transform: none;
  box-shadow: none;
}

.error-message,
.sidebar-error {
  margin: 0;
  padding: 0 24px 14px;
  color: var(--color-danger);
  font-size: 13px;
  font-weight: 500;
}

.composer {
  flex-shrink: 0;
  display: flex;
  align-items: stretch;
  gap: 12px;
  padding: 20px 24px;
  border-top: 1px solid var(--color-border-light);
  background: var(--color-surface-dim);
}

.composer button {
  min-width: 96px;
  padding-inline: 20px;
  background: var(--color-accent);
  border-color: transparent;
  color: #ffffff;
  box-shadow: 0 2px 10px rgba(0, 113, 227, 0.18);
}
.composer button:hover:not(:disabled) {
  box-shadow: 0 6px 18px rgba(0, 113, 227, 0.22);
  transform: translateY(-2px);
}

.sidebar {
  display: flex;
  flex-direction: column;
}

.tabs {
  display: flex;
  gap: 8px;
  padding: 16px 24px 12px;
  border-bottom: 1px solid var(--color-border-light);
}

.tab-button {
  min-width: 80px;
}

.tab-button.active {
  background: var(--color-accent);
  border-color: transparent;
  color: #ffffff;
  box-shadow: 0 2px 10px rgba(0, 113, 227, 0.18);
}

.sidebar-list {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 16px 24px 24px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.sidebar-card {
  padding: 16px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-surface-raised);
  display: flex;
  flex-direction: column;
  gap: 12px;
  transition: all var(--duration-base) var(--ease-out-expo);
}
.sidebar-card:hover {
  background: var(--color-surface-hover);
  border-color: rgba(0, 113, 227, 0.25);
  transform: translateY(-3px);
  box-shadow: var(--shadow-md);
}

.card-top {
  display: flex;
  gap: 12px;
  justify-content: space-between;
  align-items: flex-start;
}

.card-title {
  font-size: 15px;
  line-height: 1.5;
  color: var(--color-text-primary);
  font-weight: 600;
}

.card-amount {
  flex-shrink: 0;
  color: var(--color-text-primary);
  font-weight: 700;
}

.card-meta {
  font-size: 14px;
  color: var(--color-text-secondary);
}

.bot-text-row { display: flex; align-items: flex-start; gap: 8px; }
.bot-text-row p { flex: 1; margin: 0; }
.bot-actions {
  display: flex; gap: 6px; flex-shrink: 0; align-items: center;
}
.tts-button, .copy-button {
  flex-shrink: 0; width: 32px; height: 32px; padding: 0;
  border: 1px solid var(--color-border-light); border-radius: 8px;
  background: var(--color-surface); cursor: pointer;
  font-size: 14px; display: inline-flex; align-items: center; justify-content: center;
  transition: all var(--duration-base) var(--ease-out-expo); color: var(--color-text-muted);
}
.tts-button:hover:not(:disabled), .copy-button:hover:not(:disabled) {
  background: var(--color-accent-soft); border-color: var(--color-accent); color: var(--color-accent-strong);
  transform: scale(1.1);
}
.tts-button:disabled, .copy-button:disabled { cursor: not-allowed; opacity: 0.65; }
.tts-button.tts-playing { background: var(--color-accent-soft); border-color: var(--color-accent); color: var(--color-accent-strong); }
.tts-bars {
  display: inline-flex; align-items: flex-end; gap: 3px; height: 16px;
}
.tts-bars span {
  width: 3px;
  background: var(--color-accent);
  border-radius: 2px;
  animation: barBounce 0.6s ease-in-out infinite;
}
.tts-bars span:nth-child(1) { height: 8px; animation-delay: 0s; }
.tts-bars span:nth-child(2) { height: 14px; animation-delay: 0.15s; }
.tts-bars span:nth-child(3) { height: 10px; animation-delay: 0.3s; }
@keyframes barBounce {
  0%, 100% { transform: scaleY(0.5); }
  50% { transform: scaleY(1); }
}
.tts-spinner {
  width: 14px; height: 14px;
  border: 2px solid var(--color-accent-soft); border-top-color: var(--color-accent);
  border-radius: 50%; animation: tts-spin 0.6s linear infinite;
}
@keyframes tts-spin { to { transform: rotate(360deg); } }
.copy-button.copy-done {
  background: var(--color-success-soft);
  border-color: var(--color-success);
  color: var(--color-success);
}

.suggestion-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 10px;
  padding-top: 10px;
  border-top: 1px solid var(--color-border-light);
}
.suggestion-chip {
  padding: 6px 14px;
  border: 1px solid rgba(0, 0, 0, 0.08);
  border-radius: var(--radius-full);
  background: #f5f5f7;
  color: var(--color-text-primary);
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all var(--duration-base) var(--ease-out-expo);
}
.suggestion-chip:hover:not(:disabled) {
  background: #e5e5ea;
  border-color: rgba(0, 0, 0, 0.12);
  transform: translateY(-1px);
}
.suggestion-chip:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.full-width {
  width: 100%;
}

.sidebar .secondary-button.full-width {
  min-height: 42px;
}

.sidebar-empty {
  margin: auto;
  max-width: 420px;
  color: var(--color-text-muted);
  text-align: center;
  line-height: 1.7;
}

/* Turn 卡片中的对象卡片样式调整 */
.turn-bubble .object-card {
  min-width: 200px;
  background: #ffffff;
  border: 1px solid rgba(0, 0, 0, 0.06);
  border-radius: 12px;
  padding: 10px;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04);
}

.user-bubble .object-card-badge {
  background: rgba(0, 113, 227, 0.10);
  color: var(--color-accent-strong);
}

.bot-bubble .object-card-badge {
  background: rgba(0, 113, 227, 0.10);
  color: var(--color-accent-strong);
}

@media (max-width: 1180px) {
  .workspace {
    grid-template-columns: 1fr;
  }

  .chat-header {
    flex-direction: column;
  }

  .header-actions {
    width: 100%;
    justify-content: space-between;
    flex-wrap: wrap;
  }

  .sidebar {
    min-height: auto;
    height: auto;
  }
}

@media (max-width: 720px) {
  .app-shell {
    padding: 0;
  }

  .workspace {
    gap: 0;
  }

  .chat-card,
  .sidebar {
    min-height: auto;
    height: auto;
    border-radius: 0;
    border-left: none;
    border-right: none;
  }

  .chat-card {
    min-height: 100vh;
  }

  .message {
    max-width: 100%;
  }

  .composer,
  .field-row {
    flex-direction: column;
    align-items: stretch;
  }
}

.digital-human {
  display: flex;
  flex-direction: column;
  min-height: calc(100vh - 48px);
  height: calc(100vh - 48px);
  padding: 20px;
  gap: 14px;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  overflow: hidden;
  box-shadow: var(--shadow-lg), var(--shadow-inner-glow);
}
.dh-header { display: flex; align-items: center; gap: 12px; }
.dh-avatar {
  position: relative; width: 44px; height: 44px; border-radius: 50%;
  background: linear-gradient(135deg, var(--color-accent), var(--color-info));
  flex-shrink: 0; overflow: hidden;
}
.dh-avatar-img {
  width: 100%; height: 100%; object-fit: cover; display: block;
}
.dh-avatar.online { box-shadow: 0 0 18px var(--color-accent-glow); }
.dh-status-dot {
  position: absolute; bottom: 0; right: 0; width: 12px; height: 12px;
  border-radius: 50%; background: var(--color-text-muted); border: 2px solid var(--color-surface);
}
.dh-avatar.online .dh-status-dot { background: var(--color-success); animation: pulse 2s infinite; }
.dh-meta { display: flex; flex-direction: column; gap: 2px; }
.dh-name { font-size: 15px; font-weight: 600; color: var(--color-text-primary); }
.dh-state { font-size: 12px; color: var(--color-text-secondary); }
.dh-stage {
  position: relative; flex: 0 0 auto; width: 100%; aspect-ratio: 9 / 16;
  max-width: 100%; max-height: calc(100vh - 220px); margin: 0 auto;
  border-radius: var(--radius-md);
  background: #f5f5f7; overflow: hidden; display: flex; align-items: center; justify-content: center;
}
#digital-human-sdk { width: 100%; height: 100%; overflow: hidden; }
#digital-human-sdk canvas,
#digital-human-sdk video {
  width: 100% !important;
  height: 100% !important;
  object-fit: contain !important;
  object-position: center center !important;
  /* 魔珐 SDK 输出的人物在画面内略偏右，通过放大+左移做视觉居中补偿 */
  transform: scale(1.15) translateX(-6%);
}
.dh-placeholder {
  position: absolute; inset: 0; display: flex; flex-direction: column; align-items: center; justify-content: center;
  text-align: center; color: var(--color-text-muted); font-size: 14px; line-height: 1.8; padding: 16px;
  pointer-events: none;
  background: #f5f5f7;
}
.dh-placeholder-icon {
  font-size: 40px;
  margin-bottom: 12px;
  opacity: 0.55;
}
.dh-progress { height: 6px; background: var(--color-surface-field); border-radius: 3px; overflow: hidden; }
.dh-progress-bar { height: 100%; width: 0%; background: linear-gradient(90deg, var(--color-accent), var(--color-info)); transition: width .3s; }
.dh-button {
  min-height: 44px; padding: 10px 16px; border: 1px solid transparent; border-radius: var(--radius-md);
  background: var(--color-accent); color: #ffffff;
  font-size: 14px; font-weight: 600; cursor: pointer; transition: all var(--duration-base) var(--ease-out-expo);
}
.dh-button:disabled { opacity: 0.6; cursor: not-allowed; }
.dh-button.danger { background: var(--color-danger); }
.dh-error { margin: 0; color: var(--color-danger); font-size: 12px; }

@media (max-width: 1180px) {
  .digital-human { min-height: auto; height: 420px; }
  .dh-stage { max-height: 100%; }
}
</style>
