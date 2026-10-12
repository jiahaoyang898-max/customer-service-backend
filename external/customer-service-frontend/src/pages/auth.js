/**
 * 轻量本地账号存储
 * ------------------------------------------------------------
 * 本项目的后端暂未提供用户认证接口，为了「保持原有代码不动」，
 * 登录 / 注册页采用浏览器本地存储实现一套可真实走通的账号闭环：
 *   · 用户注册后账号写入 localStorage，可立即用于登录
 *   · 登录成功后写入会话标记，跳转回工作台首页
 *   · 不内置任何预置 / 演示账号，需由用户自行注册
 * 若后续后端提供 /api/auth 接口，只需替换本文件中的实现即可。
 */

const ACCOUNTS_KEY = 'cs_accounts'
const SESSION_KEY = 'cs_session'
const REMEMBER_KEY = 'cs_remember_account'

/** 读取已注册账号 */
export function loadAccounts() {
  try {
    const raw = localStorage.getItem(ACCOUNTS_KEY)
    const list = raw ? JSON.parse(raw) : []
    return Array.isArray(list) ? list : []
  } catch {
    return []
  }
}

/** 保存账号列表 */
function saveAccounts(list) {
  try {
    localStorage.setItem(ACCOUNTS_KEY, JSON.stringify(list))
  } catch {
    /* 隐私模式下写入失败，忽略 */
  }
}

/** 账号是否已存在 */
export function accountExists(account) {
  const normalized = normalize(account)
  return loadAccounts().some((item) => normalize(item.account) === normalized)
}

/** 注册：写入本地账号列表 */
export function register({ name, account, password }) {
  const list = loadAccounts()
  const record = { name: name.trim(), account: account.trim(), password, createdAt: Date.now() }
  list.push(record)
  saveAccounts(list)
  return { name: record.name, account: record.account }
}

/** 登录：仅校验已注册账号 */
export function login({ account, password, remember }) {
  const normalized = normalize(account)
  const matched = loadAccounts().find((item) => normalize(item.account) === normalized)

  if (!matched) {
    return { ok: false, message: '该账号尚未注册，请先注册后再登录。' }
  }
  if (matched.password !== password) {
    return { ok: false, message: '密码不正确，请重新输入。' }
  }

  const session = { account: matched.account, name: matched.name, loginAt: Date.now() }
  try {
    localStorage.setItem(SESSION_KEY, JSON.stringify(session))
    if (remember) localStorage.setItem(REMEMBER_KEY, matched.account)
    else localStorage.removeItem(REMEMBER_KEY)
  } catch {
    /* 忽略存储异常 */
  }

  return { ok: true, session }
}

/** 退出登录 */
export function logout() {
  try {
    localStorage.removeItem(SESSION_KEY)
  } catch {
    /* 忽略 */
  }
}

/** 读取当前会话 */
export function getSession() {
  try {
    const raw = localStorage.getItem(SESSION_KEY)
    return raw ? JSON.parse(raw) : null
  } catch {
    return null
  }
}

/** 读取「记住我」的账号 */
export function getRememberedAccount() {
  try {
    return localStorage.getItem(REMEMBER_KEY) || ''
  } catch {
    return ''
  }
}

function normalize(value) {
  return String(value || '').trim().toLowerCase()
}
