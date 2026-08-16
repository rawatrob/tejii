/* Tejii — shared chrome + helpers. Loaded by every page.
   Put <body data-page="home|seekhein|practice|scanner|khabrein|watchlist"> and the
   header, mobile nav and footer render themselves. One place to change them all. */

const $ = s => document.querySelector(s);
const $$ = s => [...document.querySelectorAll(s)];
const esc = s => { const n = document.createElement('div'); n.textContent = s ?? ''; return n.innerHTML; };
const sign = v => v > 0 ? 'up' : v < 0 ? 'dn' : 'mut';
const arrow = v => v > 0 ? '▲' : v < 0 ? '▼' : '■';
const pc = v => (v > 0 ? '+' : '') + Number(v).toFixed(2) + '%';
const inr = v => Number(v).toLocaleString('en-IN', {maximumFractionDigits: 2});

const NAV = [
  {id: 'home',      href: 'index.html',     label: 'होम'},
  {id: 'seekhein',  href: 'seekhein.html',  label: 'सीखें'},
  {id: 'practice',  href: 'practice.html',  label: 'Practice'},
  {id: 'scanner',   href: 'scanner.html',   label: 'Scanner'},
  {id: 'khabrein',  href: 'khabrein.html',  label: 'खबरें'},
  {id: 'watchlist', href: 'watchlist.html', label: 'Watchlist'},
];

function chrome() {
  const page = document.body.dataset.page || '';
  const ic = i => `<i class="ni${i ? ' i' + i : ''}"></i>`;

  document.body.insertAdjacentHTML('afterbegin', `
  <a class="skip" href="#main">सीधे मुख्य सामग्री पर जाएं</a>
  <header><div class="wrap hrow">
    <a class="logo" href="index.html"><img src="img/logo.png" alt=""><b>Tejii</b></a>
    <nav>${NAV.map((n, i) =>
      `<a href="${n.href}"${n.id === page ? ' class="on" aria-current="page"' : ''}>${ic(i)}${n.label}</a>`).join('')}</nav>
    <div class="hsearch"><input id="q" placeholder="शेयर या खबर खोजें…" autocomplete="off"
      aria-label="शेयर या खबर खोजें"></div>
    <a class="btn" href="#">लॉगिन / साइनअप</a>
  </div></header>`);

  document.body.insertAdjacentHTML('beforeend', `
  <footer><div class="wrap">
    <div class="fgrid">
      <div>
        <div class="logo" style="margin-bottom:9px"><img src="img/logo.png" alt=""><b style="color:#fff">Tejii</b></div>
        <p style="line-height:1.7;max-width:300px">एक शिक्षात्मक मंच जो आपको बाजार समझने और
          बेहतर निवेशक बनने में मदद करता है। हम कोई शेयर खरीदने-बेचने की सलाह नहीं देते।</p>
      </div>
      <div><h4>सीखें</h4><ul>
        <li><a href="seekhein.html#share-market-kya-hai">शेयर बाजार क्या है?</a></li>
        <li><a href="seekhein.html#paise-lagane-se-pehle">निवेश से पहले</a></li>
        <li><a href="seekhein.html#sip-kya-hai">SIP क्या है?</a></li>
        <li><a href="seekhein.html#index-fund">Index Fund</a></li>
        <li><a href="seekhein.html#market-gir-raha-hai">बाजार गिर रहा है?</a></li></ul></div>
      <div><h4>Practice</h4><ul>
        <li><a href="practice.html">वर्चुअल ट्रेडिंग</a></li>
        <li><a href="watchlist.html">मेरी Watchlist</a></li></ul></div>
      <div><h4>टूल्स</h4><ul>
        <li><a href="scanner.html">स्टॉक स्कैनर</a></li>
        <li><a href="khabrein.html">बाजार समाचार</a></li></ul></div>
      <div><h4>हमेशा याद रखें</h4><ul class="remember">
        <li><span>🚫</span>हम टिप्स नहीं देते</li>
        <li><span>⚠️</span>कोई गारंटी नहीं होती</li>
        <li><span>📚</span>सीखना पहले, निवेश बाद में</li>
        <li><span>💰</span>वही पैसा लगाएं जो 5 साल न चाहिए</li></ul></div>
    </div>
    <p class="disc"><b style="color:#fff">जरूरी सूचना:</b>
      Tejii SEBI-पंजीकृत रिसर्च एनालिस्ट या निवेश सलाहकार <b>नहीं</b> है। इस वेबसाइट पर दी गई
      कोई भी जानकारी शेयर खरीदने या बेचने की सलाह नहीं है — यह सिर्फ शिक्षा और जानकारी के लिए है।
      सभी आंकड़े NSE के सार्वजनिक end-of-day डेटा से लिए गए हैं और इनमें देरी हो सकती है।
      शेयर बाजार में निवेश जोखिम भरा है और आपका पैसा घट सकता है।
      निवेश से पहले अपनी समझ बनाएं या किसी पंजीकृत सलाहकार से बात करें।
      <span id="stamp"></span></p>
  </div></footer>

  <div class="mnav">${NAV.slice(0, 5).map((n, i) =>
    `<a href="${n.href}"${n.id === page ? ' class="on"' : ''}>${ic(i)}${n.label}</a>`).join('')}</div>`);

  $('#q').onkeydown = e => {
    if (e.key === 'Enter' && e.target.value.trim())
      location.href = 'scanner.html#' + encodeURIComponent(e.target.value.trim());
  };
}

/* home.json is small and every page wants the date stamp / index values */
const homeData = () => fetch('data/home.json?v=' + Date.now()).then(r => r.json());

function stamp(d) {
  const s = $('#stamp');
  if (s) s.innerHTML = `<br>डेटा: ${hindiDate(d.date)} का बंद भाव · अपडेट ${esc(d.built_at.replace('T', ' '))} IST`;
}

function hindiDate(iso) {
  const M = ['जनवरी','फरवरी','मार्च','अप्रैल','मई','जून','जुलाई','अगस्त','सितंबर','अक्टूबर','नवंबर','दिसंबर'];
  const D = ['रविवार','सोमवार','मंगलवार','बुधवार','गुरुवार','शुक्रवार','शनिवार'];
  const [y, m, d] = iso.split('-').map(Number), dt = new Date(Date.UTC(y, m - 1, d));
  return `${d} ${M[m - 1]} ${y}, ${D[dt.getUTCDay()]}`;
}

function ago(ts) {
  const m = Math.max(0, Math.round((Date.now() / 1000 - ts) / 60));
  if (m < 60) return m + ' मिनट पहले';
  if (m < 1440) return Math.round(m / 60) + ' घंटे पहले';
  return Math.round(m / 1440) + ' दिन पहले';
}

/* watchlist lives in the browser — no login needed to try it */
const WL = {
  get: () => { try { return JSON.parse(localStorage.tejii_wl || '[]'); } catch { return []; } },
  set(v) { try { localStorage.tejii_wl = JSON.stringify([...new Set(v)]); } catch {} },
  has(s) { return this.get().includes(s); },
  toggle(s) { const l = this.get(); this.set(l.includes(s) ? l.filter(x => x !== s) : [...l, s]); return this.has(s); },
};

chrome();
