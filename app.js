const DD = "https://ddragon.leagueoflegends.com";
const ROLE = {TOP:"탑",JUNGLE:"정글",MIDDLE:"미드",BOTTOM:"원딜",UTILITY:"서폿"};
const $ = id => document.getElementById(id);
let D, ver, items, runes = {}, champs;

const j = async u => { const r = await fetch(u); if (!r.ok) throw new Error(u); return r.json(); };
const cname = id => champs[id]?.name || id;
const pct = (a, b) => b ? (a / b * 100).toFixed(1) : "0.0";

async function init() {
  try {
    ver = (await j(DD + "/api/versions.json"))[0];
    const [b, it, ru, ch] = await Promise.all([
      j("data/builds.json"),
      j(`${DD}/cdn/${ver}/data/ko_KR/item.json`),
      j(`${DD}/cdn/${ver}/data/ko_KR/runesReforged.json`),
      j(`${DD}/cdn/${ver}/data/ko_KR/champion.json`)
    ]);
    D = b; items = it.data; champs = ch.data;
    ru.forEach(t => {
      runes[t.id] = { name: t.name, icon: t.icon };
      t.slots.forEach(s => s.runes.forEach(r => runes[r.id] = { name: r.name, icon: r.icon }));
    });
    $("meta").textContent = `패치 ${D.patch} · ${D.matches}경기 · 갱신 ${D.updated} · 한국 챌린저/그마 솔로랭크`;
    const keys = Object.keys(D.champions).sort((a, b) => D.champions[b].games - D.champions[a].games);
    if (!keys.length) { $("view").innerHTML = '<div class="card">데이터가 아직 없어요. Actions에서 update-data를 한 번 실행하세요.</div>'; return; }
    $("champ").innerHTML = keys.map(k => {
      const [c, r] = k.split("|");
      return `<option value="${k}">${cname(c)} (${ROLE[r] || r}) · ${D.champions[k].games}판</option>`;
    }).join("");
    $("champ").onchange = fillOpp;
    $("opp").onchange = render;
    fillOpp();
  } catch (e) { $("meta").textContent = "불러오기 실패: " + e.message; }
}

function fillOpp() {
  const vs = D.champions[$("champ").value].vs;
  const ks = Object.keys(vs).sort((a, b) => vs[b].games - vs[a].games);
  $("opp").innerHTML = '<option value="">전체 (상대 무관)</option>' +
    ks.map(k => `<option value="${k}">vs ${cname(k)} · ${vs[k].games}판</option>`).join("");
  render();
}

function list(map, total, kind) {
  return Object.entries(map).sort((a, b) => b[1][0] - a[1][0]).slice(0, 10).map(([id, [g, w]]) => {
    const isItem = kind === "item";
    const o = isItem ? items[id] : runes[id];
    const img = isItem ? `${DD}/cdn/${ver}/img/item/${id}.png` : `${DD}/cdn/img/${o?.icon}`;
    const wr = pct(w, g);
    return `<div class="row"><img src="${img}" alt="" onerror="this.style.visibility='hidden'">
      <span class="n">${o?.name || id}</span>
      <span class="s">픽률 ${pct(g, total)}%<br><span class="${wr >= 50 ? "win" : "lose"}">승률 ${wr}%</span> (${g}판)</span></div>`;
  }).join("") || "<div class='row'>데이터 없음</div>";
}

function render() {
  const c = D.champions[$("champ").value], o = $("opp").value;
  const b = o ? c.vs[o] : c;
  const wr = pct(b.wins, b.games);
  $("view").innerHTML = `
    <div class="card"><h2>${o ? "vs " + cname(o) : "전체"} — ${b.games}판 · 승률 ${wr}%${b.games < 10 ? " (표본 적음)" : ""}</h2></div>
    <div class="card"><h2>완성 아이템</h2>${list(b.items, b.games, "item")}</div>
    <div class="card"><h2>핵심 룬</h2>${list(b.keystone, b.games, "rune")}</div>
    <div class="card"><h2>보조 룬 계열</h2>${list(b.sub, b.games, "rune")}</div>`;
}
init();
