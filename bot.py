import asyncio, sqlite3, re, os, threading, urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200); self.end_headers()
        self.wfile.write(b"Bot is running!")
    def log_message(self, *args): pass
def run_web():
    port = int(os.getenv("PORT", 10000))
    HTTPServer(("0.0.0.0", port), Handler).serve_forever()
threading.Thread(target=run_web, daemon=True).start()

TOKEN = os.getenv("BOT_TOKEN")
bot = Bot(token=TOKEN)
dp = Dispatcher()
conn = sqlite3.connect("mal.db", check_same_thread=False)
cur = conn.cursor()
cur.execute("CREATE TABLE IF NOT EXISTS listings (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, username TEXT, category TEXT, title TEXT, price TEXT, price_num INTEGER, phone TEXT, location TEXT, city TEXT, description TEXT, photo_id TEXT, media_type TEXT DEFAULT 'photo', views INTEGER DEFAULT 0, status TEXT DEFAULT 'active')")
cur.execute("CREATE TABLE IF NOT EXISTS favs (user_id INTEGER, listing_id INTEGER, UNIQUE(user_id, listing_id))")
conn.commit()
for col in ["media_type TEXT DEFAULT 'photo'", "views INTEGER DEFAULT 0"]:
    try:
        cur.execute(f"ALTER TABLE listings ADD COLUMN {col}"); conn.commit()
    except: pass
CATEGORIES = ["🐑 Кой", "🐄 Уй", "🐐 Эчки", "🐓 Тоок", "🐴 Ат", "🐖 Чочко", "🐫 Төө", "🐇 Коён", "🦆 Өрдөк / Каз", "📦 Башка"]
CITIES = ["🌍 Баары", "📍 Ош", "📍 Бишкек", "📍 Жалал-Абад", "📍 Баткен", "📍 Кызыл-Кыя", "📍 Нарын", "📍 Талас", "📍 Ысык-Көл", "📍 Чүй"]
PRICES = ["💰 Баары", "💰 10000 чейин", "💰 10000 - 30000", "💰 30000 - 50000", "💰 50000 - 100000", "💰 100000 жогору"]
class Add(StatesGroup):
    category = State(); title = State(); media = State(); price = State(); phone = State(); city = State(); location = State(); description = State()
class Browse(StatesGroup):
    category = State(); city = State(); price = State()
def parse_price(t):
    n = re.findall(r'\d+', t.replace(' ', ''))
    return int(''.join(n)) if n else 0
def price_range(l):
    if "10000 чейин" in l: return (0, 10000)
    if "10000 - 30000" in l: return (10000, 30000)
    if "30000 - 50000" in l: return (30000, 50000)
    if "50000 - 100000" in l: return (50000, 100000)
    if "100000 жогору" in l: return (100000, 999999999)
    return (0, 999999999)
def main_kb():
    return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="🛒 Мал көрүү"), KeyboardButton(text="➕ Мал сатуу")],[KeyboardButton(text="📋 Менин жарыяларым"), KeyboardButton(text="❤️ Сакталгандар")],[KeyboardButton(text="ℹ️ Жардам")]], resize_keyboard=True)
def cats_kb():
    kb=[]
    for i in range(0, len(CATEGORIES), 2):
        r=[KeyboardButton(text=CATEGORIES[i])]
        if i+1 < len(CATEGORIES): r.append(KeyboardButton(text=CATEGORIES[i+1]))
        kb.append(r)
    kb.append([KeyboardButton(text="⬅️ Артка")])
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)
def cities_kb():
    kb=[]
    for i in range(0, len(CITIES), 2):
        r=[KeyboardButton(text=CITIES[i])]
        if i+1 < len(CITIES): r.append(KeyboardButton(text=CITIES[i+1]))
        kb.append(r)
    kb.append([KeyboardButton(text="⬅️ Артка")])
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)
def prices_kb():
    kb=[[KeyboardButton(text=p)] for p in PRICES]
    kb.append([KeyboardButton(text="⬅️ Артка")])
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def make_kb(lid, phone, username, city, loc, title, price, is_owner, is_fav):
    clean = re.sub(r'[^+\d]', '', str(phone or ''))
    rows = []
    if is_owner:
        rows.append([InlineKeyboardButton(text="✅ Сатылды", callback_data=f"sold:{lid}")])
    else:
        r = []
        if clean and len(clean) >= 9:
            r.append(InlineKeyboardButton(text="📞 Чалуу", url=f"tel:{clean}"))
        if username and str(username).startswith("@"):
            r.append(InlineKeyboardButton(text="💬 Жазуу", url=f"https://t.me/{str(username)[1:]}"))
        if r: rows.append(r)
    fav_txt = "💔 Сакталгандан алуу" if is_fav else "❤️ Сактоо"
    rows.append([InlineKeyboardButton(text=fav_txt, callback_data=f"fav:{lid}")])
    share_txt = urllib.parse.quote(f"Мал Базар: {title} - {price} \nhttps://t.me/mal_charba_bazar_bot")
    rows.append([InlineKeyboardButton(text="📤 Бөлүшүү", url=f"https://t.me/share/url?text={share_txt}")])
    if loc:
        q = urllib.parse.quote(str(loc))
        rows.append([InlineKeyboardButton(text="📍 Картадан көрүү", url=f"https://maps.google.com/?q={q}")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

async def send_listing(m, row, viewer_id):
    lid, title, price, phone, loc, cty, desc, media_id, media_type, user, owner, views, cat = row
    cur.execute("UPDATE listings SET views=views+1 WHERE id=?", (lid,))
    conn.commit(); views = (views or 0) + 1
    cur.execute("SELECT 1 FROM favs WHERE user_id=? AND listing_id=?", (viewer_id, lid))
    is_fav = cur.fetchone() is not None
    cap = f"{cat}\n\n📌 {title}\n💰 {price}\n🏙️ {cty}\n📍 {loc}\n📞 {phone}\n👤 {user}\n📝 {desc}\n👁️ {views} жолу каралды\n\n🆔 №{lid}"
    kb = make_kb(lid, phone, user, cty, loc, title, price, owner==viewer_id, is_fav)
    try:
        if media_type == "video":
            await m.answer_video(video=media_id, caption=cap, reply_markup=kb)
        elif media_id:
            await m.answer_photo(photo=media_id, caption=cap, reply_markup=kb)
        else:
            await m.answer(cap, reply_markup=kb)
    except:
        try: await m.answer(cap, reply_markup=kb)
        except: await m.answer(cap)

@dp.message(Command("start"))
async def start(m: types.Message):
    await m.answer("👋 Салам! Мал Базарга кош келдиң!\n\n🛒 Мал көрүү - фильтр менен\n➕ Мал сатуу - Фото/Видео менен\n❤️ Сакталгандар - жакканын сакта\n\nТөмөндөн танда 👇", reply_markup=main_kb())
@dp.message(F.text == "ℹ️ Жардам")
async def help_cmd(m: types.Message):
    await m.answer("❓ Сатуу: ➕ Мал сатуу\nКөрүү: 🛒 Мал көрүү\nСактоо: жарыядагы ❤️ Сактоо бас\nСатылды: 📋 Менин жарыяларым -> ✅ Сатылды")
@dp.message(F.text == "➕ Мал сатуу")
async def add_start(m: types.Message, state: FSMContext):
    await state.set_state(Add.category); await m.answer("Категория танда:", reply_markup=cats_kb())
@dp.message(Add.category)
async def add_cat(m: types.Message, state: FSMContext):
    if m.text == "⬅️ Артка":
        await state.clear(); await m.answer("Башкы меню", reply_markup=main_kb()); return
    if m.text not in CATEGORIES:
        await m.answer("Тизмеден танда 👇", reply_markup=cats_kb()); return
    await state.update_data(category=m.text); await state.set_state(Add.title)
    await m.answer("✏️ Мал жөнүндө жаз:")
@dp.message(Add.title)
async def add_title(m: types.Message, state: FSMContext):
    await state.update_data(title=m.text); await state.set_state(Add.media)
    await m.answer("📸🎥 Сүрөт же видео жөнөт:")
@dp.message(Add.media, F.photo)
async def add_p(m: types.Message, state: FSMContext):
    await state.update_data(media_id=m.photo[-1].file_id, media_type="photo"); await state.set_state(Add.price); await m.answer("💰 Баасын жаз:")
@dp.message(Add.media, F.video)
async def add_v(m: types.Message, state: FSMContext):
    await state.update_data(media_id=m.video.file_id, media_type="video"); await state.set_state(Add.price); await m.answer("🎥 Видео кабыл алынды ✅\n💰 Баасын жаз:")
@dp.message(Add.media)
async def add_e(m: types.Message):
    await m.answer("Сураныч, сүрөт же видео жөнөт 📸🎥")
@dp.message(Add.price)
async def add_price(m: types.Message, state: FSMContext):
    await state.update_data(price=m.text, price_num=parse_price(m.text)); await state.set_state(Add.phone)
    kb = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="📱 Номеримди жөнөтүү", request_contact=True)]], resize_keyboard=True)
    await m.answer("📞 Телефон:", reply_markup=kb)
@dp.message(Add.phone, F.contact)
async def add_pc(m: types.Message, state: FSMContext):
    await state.update_data(phone=m.contact.phone_number); await state.set_state(Add.city); await m.answer("🏙️ Шаар:", reply_markup=cities_kb())
@dp.message(Add.phone)
async def add_pt(m: types.Message, state: FSMContext):
    await state.update_data(phone=m.text); await state.set_state(Add.city); await m.answer("🏙️ Шаар:", reply_markup=cities_kb())
@dp.message(Add.city)
async def add_city(m: types.Message, state: FSMContext):
    city = m.text.replace("📍 ", "").replace("🌍 ", "")
    await state.update_data(city=city); await state.set_state(Add.location); await m.answer("📍 Дарегиңди жаз:")
@dp.message(Add.location)
async def add_loc(m: types.Message, state: FSMContext):
    await state.update_data(location=m.text); await state.set_state(Add.description); await m.answer("📝 Кошумча жаз, жок болсо - деп жаз:")
@dp.message(Add.description)
async def add_desc(m: types.Message, state: FSMContext):
    d = await state.get_data(); desc = "" if m.text == "-" else m.text
    user = f"@{m.from_user.username}" if m.from_user.username else m.from_user.full_name
    cur.execute("INSERT INTO listings (user_id, username, category, title, price, price_num, phone, location, city, description, photo_id, media_type, views, status) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,0,'active')", (m.from_user.id, user, d['category'], d['title'], d['price'], d.get('price_num',0), d['phone'], d['location'], d.get('city',''), desc, d.get('media_id',''), d.get('media_type','photo')))
    conn.commit(); lid = cur.lastrowid; await state.clear()
    row = (lid, d['title'], d['price'], d['phone'], d['location'], d.get('city',''), desc, d.get('media_id',''), d.get('media_type','photo'), user, m.from_user.id, 0, d['category'])
    await send_listing(m, row, m.from_user.id)
    await m.answer("✅ Жарыяң кошулду!", reply_markup=main_kb())
@dp.message(F.text == "🛒 Мал көрүү")
async def view_start(m: types.Message, state: FSMContext):
    await state.set_state(Browse.category); await m.answer("1️⃣ Кайсы мал?", reply_markup=cats_kb())
@dp.message(Browse.category)
async def b_cat(m: types.Message, state: FSMContext):
    if m.text == "⬅️ Артка":
        await state.clear(); await m.answer("Башкы меню", reply_markup=main_kb()); return
    if m.text not in CATEGORIES:
        await m.answer("Тизмеден танда 👇", reply_markup=cats_kb()); return
    await state.update_data(category=m.text); await state.set_state(Browse.city); await m.answer(f"2️⃣ {m.text} - Кайсы шаар?", reply_markup=cities_kb())
@dp.message(Browse.city)
async def b_city(m: types.Message, state: FSMContext):
    if m.text == "⬅️ Артка":
        await state.set_state(Browse.category); await m.answer("Категория:", reply_markup=cats_kb()); return
    city = m.text.replace("📍 ", "").replace("🌍 ", "")
    await state.update_data(city=city); await state.set_state(Browse.price); await m.answer("3️⃣ Баасы?", reply_markup=prices_kb())
@dp.message(Browse.price)
async def b_price(m: types.Message, state: FSMContext):
    if m.text == "⬅️ Артка":
        await state.set_state(Browse.city); await m.answer("Шаар:", reply_markup=cities_kb()); return
    if m.text not in PRICES:
        await m.answer("Тизмеден танда 👇", reply_markup=prices_kb()); return
    d = await state.get_data(); cat = d['category']; city = d.get('city','Баары'); lo, hi = price_range(m.text); await state.clear()
    if city == "Баары":
        cur.execute("SELECT id, title, price, phone, location, city, description, photo_id, media_type, username, user_id, views, category FROM listings WHERE category=? AND status='active' AND price_num BETWEEN ? AND ? ORDER BY id DESC LIMIT 20", (cat, lo, hi))
    else:
        cur.execute("SELECT id, title, price, phone, location, city, description, photo_id, media_type, username, user_id, views, category FROM listings WHERE category=? AND status='active' AND city=? AND price_num BETWEEN ? AND ? ORDER BY id DESC LIMIT 20", (cat, city, lo, hi))
    rows = cur.fetchall()
    if not rows:
        await m.answer("😔 Жарыя жок.", reply_markup=main_kb()); return
    await m.answer(f"✅ Табылды: {len(rows)} жарыя", reply_markup=main_kb())
    for r in rows: await send_listing(m, r, m.from_user.id)
@dp.callback_query(F.data.startswith("fav:"))
async def fav_cb(cb: types.CallbackQuery):
    lid = int(cb.data.split(":")[1])
    cur.execute("SELECT 1 FROM favs WHERE user_id=? AND listing_id=?", (cb.from_user.id, lid))
    if cur.fetchone():
        cur.execute("DELETE FROM favs WHERE user_id=? AND listing_id=?", (cb.from_user.id, lid)); conn.commit(); await cb.answer("💔 Сакталгандан алынды")
    else:
        cur.execute("INSERT OR IGNORE INTO favs VALUES (?,?)", (cb.from_user.id, lid)); conn.commit(); await cb.answer("❤️ Сакталды!")
@dp.callback_query(F.data.startswith("sold:"))
async def sold_cb(cb: types.CallbackQuery):
    lid = int(cb.data.split(":")[1])
    cur.execute("SELECT user_id FROM listings WHERE id=?", (lid,)); row = cur.fetchone()
    if not row or row[0] != cb.from_user.id:
        await cb.answer("Бул сенин жарыяң эмес!", show_alert=True); return
    cur.execute("UPDATE listings SET status='sold' WHERE id=?", (lid,)); conn.commit()
    try:
        orig = cb.message.caption or cb.message.text or ""
        if cb.message.video or cb.message.photo: await cb.message.edit_caption(caption=orig + "\n\n❌ САТЫЛДЫ ✅", reply_markup=None)
        else: await cb.message.edit_text(text=orig + "\n\n❌ САТЫЛДЫ ✅", reply_markup=None)
    except: await cb.message.answer(f"✅ №{lid} САТЫЛДЫ!")
    await cb.answer("✅ Сатылды!")
@dp.callback_query(F.data.startswith("del:"))
async def del_cb(cb: types.CallbackQuery):
    lid = int(cb.data.split(":")[1])
    cur.execute("DELETE FROM listings WHERE id=? AND user_id=?", (lid, cb.from_user.id)); conn.commit()
    if cur.rowcount:
        await cb.message.answer(f"🗑️ №{lid} өчүрүлдү.")
        try: await cb.message.delete()
        except: pass
    await cb.answer()
@dp.message(F.text == "📋 Менин жарыяларым")
async def my_list(m: types.Message):
    cur.execute("SELECT id, category, title, price, city, status FROM listings WHERE user_id=? ORDER BY id DESC", (m.from_user.id,))
    rows = cur.fetchall()
    if not rows: await m.answer("Сенде жарыя жок."); return
    for r in rows:
        lid, cat, title, price, city, status = r
        em = "✅ Активдүү" if status == "active" else "❌ САТЫЛДЫ"
        txt = f"{cat}\n📌 {title}\n💰 {price}\n🏙️ {city}\nСтатус: {em}\n🆔 №{lid}"
        kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="✅ Сатылды", callback_data=f"sold:{lid}")] , [InlineKeyboardButton(text="🗑️ Өчүрүү", callback_data=f"del:{lid}")]]) if status=="active" else InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🗑️ Өчүрүү", callback_data=f"del:{lid}")]])
        await m.answer(txt, reply_markup=kb)
@dp.message(F.text == "❤️ Сакталгандар")
async def fav_list(m: types.Message):
    cur.execute("SELECT l.id, l.title, l.price, l.phone, l.location, l.city, l.description, l.photo_id, l.media_type, l.username, l.user_id, l.views, l.category FROM listings l JOIN favs f ON l.id=f.listing_id WHERE f.user_id=? AND l.status='active' ORDER BY l.id DESC", (m.from_user.id,))
    rows = cur.fetchall()
    if not rows: await m.answer("❤️ Сакталган жарыя жок.\nЖарыядагы ❤️ Сактоо баскычын бас."); return
    await m.answer(f"❤️ Сакталган: {len(rows)} жарыя")
    for r in rows: await send_listing(m, r, m.from_user.id)
async def main():
    print("Bot ishtep jatat...")
    await dp.start_polling(bot)
if __name__ == "__main__":
    asyncio.run(main())
