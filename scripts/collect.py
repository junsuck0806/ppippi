import os, json, time, requests
from datetime import datetime, timezone

KEY = os.environ["RIOT_API_KEY"]
H = {"X-Riot-Token": KEY}
KR = "https://kr.api.riotgames.com"
ASIA = "https://asia.api.riotgames.com"
PLAYERS = int(os.getenv("PLAYERS", 30))          # 챌린저+그마에서 뽑을 선수 수
PER_PLAYER = int(os.getenv("PER_PLAYER", 10))    # 선수당 최근 경기 수
MAX_MATCHES = int(os.getenv("MAX_MATCHES", 200)) # 분석할 총 경기 수

def get(url, params=None):
    for _ in range(5):
        time.sleep(1.3)  # 개발용 키 제한(2분 100회) 대비
        r = requests.get(url, headers=H, params=params, timeout=20)
        if r.status_code == 429:
            time.sleep(int(r.headers.get("Retry-After", 10)) + 1)
            continue
        if r.status_code == 200:
            return r.json()
        print("skip", r.status_code, url)
        return None
    return None

ver = requests.get("https://ddragon.leagueoflegends.com/api/versions.json").json()[0]
IT = requests.get(f"https://ddragon.leagueoflegends.com/cdn/{ver}/data/en_US/item.json").json()["data"]
FINAL = {int(i) for i, d in IT.items()
         if not d.get("into") and d["gold"]["total"] >= 900 and d["gold"]["purchasable"]}

def bump(m, k, win):
    a = m.setdefault(str(k), [0, 0]); a[0] += 1; a[1] += win

def bucket():
    return {"games": 0, "wins": 0, "items": {}, "keystone": {}, "sub": {}}

def add(b, p):
    w = int(p["win"]); b["games"] += 1; b["wins"] += w
    for i in range(6):
        if p[f"item{i}"] in FINAL:
            bump(b["items"], p[f"item{i}"], w)
    st = p["perks"]["styles"]
    bump(b["keystone"], st[0]["selections"][0]["perk"], w)
    bump(b["sub"], st[1]["style"], w)

# 1) 상위 랭커 puuid
puuids = []
for tier in ("challengerleagues", "grandmasterleagues"):
    d = get(f"{KR}/lol/league/v4/{tier}/by-queue/RANKED_SOLO_5x5")
    if d:
        es = sorted(d["entries"], key=lambda e: -e["leaguePoints"])[:PLAYERS // 2]
        puuids += [e["puuid"] for e in es if e.get("puuid")]

# 2) 최근 솔로랭크 경기 id
mids = []
for p in puuids:
    mids += get(f"{ASIA}/lol/match/v5/matches/by-puuid/{p}/ids",
                {"queue": 420, "count": PER_PLAYER}) or []
mids = list(dict.fromkeys(mids))[:MAX_MATCHES]

# 3) 경기 분석 (챔피언|라인 별, 라인 상대 별)
data, patch, n = {}, "", 0
for mid in mids:
    g = get(f"{ASIA}/lol/match/v5/matches/{mid}")
    if not g or g["info"]["gameDuration"] < 900:
        continue
    n += 1
    patch = ".".join(g["info"]["gameVersion"].split(".")[:2])
    ps = g["info"]["participants"]
    for p in ps:
        role = p["teamPosition"]
        if not role:
            continue
        foe = next((q for q in ps if q["teamId"] != p["teamId"] and q["teamPosition"] == role), None)
        c = data.setdefault(f'{p["championName"]}|{role}', {**bucket(), "vs": {}})
        add(c, p)
        if foe:
            add(c["vs"].setdefault(foe["championName"], bucket()), p)

def trim(b):
    b["items"] = dict(sorted(b["items"].items(), key=lambda x: -x[1][0])[:12])

for c in data.values():
    trim(c)
    for v in c["vs"].values():
        trim(v)

os.makedirs("data", exist_ok=True)
with open("data/builds.json", "w", encoding="utf-8") as f:
    json.dump({"patch": patch, "matches": n,
               "updated": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
               "champions": data}, f, ensure_ascii=False)
print("done", n, "matches")
