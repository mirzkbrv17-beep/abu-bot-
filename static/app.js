(() => {
  const tg = window.Telegram?.WebApp;
  tg?.ready?.(); tg?.expand?.();
  const $ = (id) => document.getElementById(id);
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
  const fmt = (v) => Number(v).toLocaleString("uz-UZ", {maximumFractionDigits: 4});

  function fill(id, rows, render) {
    const el = $(id);
    el.innerHTML = rows.length ? rows.map(render).join("") : '<li class="empty">Hozircha yo‘q</li>';
  }

  async function load() {
    const initData = tg?.initData || "";
    const res = await fetch("/api/me", { headers: { Authorization: "tma " + initData } });
    if (!res.ok) { $("name").textContent = "Kirish rad etildi"; return; }
    const d = await res.json();
    $("avatar").textContent = (d.name || "A").charAt(0).toUpperCase();
    $("name").textContent = d.name;
    $("abuid").textContent = "ABU ID: " + d.abu_id;
    $("vip").textContent = d.vip ? "👑 VIP" : "VIP yo‘q";
    $("bal-abu_f").textContent = fmt(d.balances.abu_f);
    $("bal-abu_ton").textContent = fmt(d.balances.abu_ton);
    $("level").textContent = d.level;
    $("xp").textContent = d.xp + " XP";
    $("xpbar").style.width = d.xp_in_level + "%";
    $("streak").textContent = d.streak;
    $("refs").textContent = d.referrals;
    fill("tx", d.transactions, t => `<li><span>${esc(t.note)}</span><span>${t.amount > 0 ? "+" : ""}${fmt(t.amount)} ${t.currency === "abu_f" ? "ABU F" : "ABU TON"}</span></li>`);
    fill("orders", d.orders, o => `<li><span>#${o.id} ${esc(o.title)}</span><span>${esc(o.status)}</span></li>`);
    fill("collection", d.collection, c => `<li><span>${esc(c.title)}</span><span>${c.serial ? "#" + c.serial : ""}</span></li>`);
  }

  async function banners() {
    const d = await (await fetch("/api/banners")).json();
    $("banners").innerHTML = d.items.map(b =>
      `<div class="banner tone-${esc(b.tone)}"><h4>${esc(b.title)}</h4><p>${esc(b.subtitle)}</p></div>`).join("");
  }

  banners().catch(() => {});
  load().catch(() => { $("name").textContent = "Xatolik"; });
})();
