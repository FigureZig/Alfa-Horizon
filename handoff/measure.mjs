// Замер экрана для приёмки из 1-redesign.md (§7): слова, кнопки, поля, экраны прокрутки, жаргон, сырые ключи перевода.
//
// Один раз:   (cd handoff && npm i --no-save playwright && npx playwright install chromium)   ← только node_modules, без package.json
// Запуск:     node handoff/measure.mjs s7 /cabinet/770100000079 /cabinet/770100000079/credits
//             node handoff/measure.mjs - /login /            ← без входа
//             MOBILE=1 node handoff/measure.mjs s7 /cabinet/770100000079
// Первый аргумент — ID пользователя (s7, s3, bank…) или «-», дальше — пути. Стенд должен быть поднят (:8080).
import { chromium } from 'playwright'

const BASE = process.env.BASE || 'http://localhost:8080'
const [who, ...paths] = process.argv.slice(2)
const JARGON = '(ДБО|МЧД|ЕИО|ЕГРЮЛ|ЕГРИП|ОКВЭД|ФЗ|ст\\. ?\\d+|скоринг|балл|класс риска|спред|SLA|воркер|персон|песочниц|демо)'

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: process.env.MOBILE ? { width: 390, height: 844 } : { width: 1440, height: 900 } })
if (who && who !== '-') {
  const res = await fetch(`${BASE}/api/v1/sandbox/personas/${who}/login?wait_s=10`, { method: 'POST' })
  const token = (await res.json()).data.token
  await page.addInitScript((t) => localStorage.setItem('fino-token', t), token)
}

for (const path of paths) {
  await page.goto(BASE + path, { waitUntil: 'networkidle' })
  await page.waitForTimeout(1500)
  const m = await page.evaluate((jargon) => {
    const vis = (e) => e.offsetParent !== null && e.getBoundingClientRect().width > 0
    const inView = (e) => { const r = e.getBoundingClientRect(); return r.top < innerHeight && r.bottom > 0 }
    const text = (document.querySelector('main') || document.body).innerText
    const controls = [...document.querySelectorAll('a,button,[role=button]')].filter(vis)
    const fields = [...document.querySelectorAll('input:not([type=hidden]),select,textarea,[role=radio],[role=checkbox],[role=switch]')].filter(vis)
    const terms = text.match(new RegExp(jargon, 'gi')) || []
    const keys = (text.match(/\b[a-z]+[A-Za-z]*\.[a-z][A-Za-z]+(\.[A-Za-z]+)*\b/g) || []).filter((s) => !/\.(ru|com|pdf|png)$/.test(s))
    return {
      words: text.split(/\s+/).filter((w) => /[A-Za-zА-Яа-яЁё]/.test(w)).length,
      controls: controls.length, firstScreen: controls.filter(inView).length, fields: fields.length,
      screens: Math.round((document.documentElement.scrollHeight / innerHeight) * 10) / 10,
      jargon: [...new Set(terms.map((t) => t.toLowerCase()))], rawKeys: [...new Set(keys)],
    }
  }, JARGON)
  const flags = [m.jargon.length && `жаргон: ${m.jargon.join(', ')}`, m.rawKeys.length && `сырые ключи: ${m.rawKeys.join(', ')}`]
  console.log(`${path.padEnd(48)} слов ${String(m.words).padStart(4)} · кнопок ${m.controls} (на первом экране ${m.firstScreen})` +
    ` · полей ${m.fields} · экранов ${m.screens}${flags.filter(Boolean).map((f) => ' · ' + f).join('')}` +
    (page.url().endsWith(path) ? '' : `  → открылось ${page.url().replace(BASE, '')}`))
}
await browser.close()
