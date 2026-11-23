import asyncio, sqlite3, re, os, threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is running!")
    def log_message(self, *args):
        pass
def run_web():
    port = int(os.getenv("PORT", 10000))
    HTTPServer(("0.0.0.0", port), Handler).serve_forever()
threading.Thread(target=run_web, daemon=True).start()

TOKEN = os.getenv("BOT_TOKEN")
bot = Bot(token=TOKEN)
dp = Dispatcher()
conn = sqlite3.connect("mal.db", check_same_thread=False)
cur = conn.cursor()
cur.execute("CREATE TABLE IF NOT EXISTS listings (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, username TEXT, category TEXT, title TEXT, price TEXT, price_num INTEGER, phone TEXT, location TEXT, city TEXT, description TEXT, photo_id TEXT, media_type TEXT DEFAULT 'photo', status TEXT DEFAULT 'active')")
conn.commit()
try:
    cur.execute("ALTER TABLE listings ADD COLUMN media_type TEXT DEFAULT 'photo'")
    conn.commit()
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
    return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="🛒 Мал көрүү"), KeyboardButton(text="➕ Мал сатуу")],[KeyboardButton(text="📋 Менин жарыяларым"), KeyboardButton(text="ℹ️ Жардам")]], resize_keyboard=True)
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

async def send_listing(m, cat, title, price, cty, loc, phone, user, desc, lid, media_id, media_type, owner_id=None, is_owner=False):
    cap = f"{cat}\n\n📌 {title}\n💰 {price}\n🏙️ {cty}\n📍 {loc}\n📞 {phone}\n👤 {user}\n📝 {desc}\n\n🆔 №{lid}"
    if is_owner:
        kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="✅ Сатылды деп белгилөө", callback_data=f"sold:{lid}")]])
    else:
        kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="📞 Чалуу", url=f"tel:{phone}")]])
    try:
        if media_type == "video":
            await m.answer_video(video=media_id, caption=cap, reply_markup=kb)
        else:
            await m.answer_photo(photo=media_id, caption=cap, reply_markup=kb)
    except:
        await m.answer(cap, reply_markup=kb)

@dp.message(Command("start"))
async def start(m: types.Message):
    await m.answer("👋 Салам! Мал Базар ботуна кош келдиң!\n\n🛒 Мал көрүү - Категория + Шаар + Баа фильтр\n➕ Мал сатуу - Фото же Видео менен сат", reply_markup=main_kb())
@dp.message(F.text == "ℹ️ Жардам")
async def help_cmd(m: types.Message):
    await m.answer("❓ Сатуу үчүн: ➕ Мал сатуу бас\nКөрүү үчүн: 🛒 Мал көрүү бас\nСатылды деп белгилөө: 📋 Менин жарыяларым -> ✅ Сатылды бас\n\n🎥 Видео да жөнөтсө болот!")
@dp.message(F.text == "➕ Мал сатуу")
async def add_start(m: types.Message, state: FSMContext):
    await state.set_state(Add.category)
    await m.answer("Категория танда:", reply_markup=cats_kb())
@dp.message(Add.category)
async def add_cat(m: types.Message, state: FSMContext):
    if m.text == "⬅️ Артка":
        await state.clear(); await m.answer("Башкы меню", reply_markup=main_kb()); return
    if m.text not in CATEGORIES:
        await m.answer("Тизмеден танда 👇", reply_markup=cats_kb()); return
    await state.update_data(category=m.text)
    await state.set_state(Add.title)
    await m.answer("✏️ Мал жөнүндө жаз:\nМисалы: 2 жашар кой, 10 баш")
@dp.message(Add.title)
async def add_title(m: types.Message, state: FSMContext):
    await state.update_data(title=m.text)
    await state.set_state(Add.media)
    await m.answer("📸🎥 Эми малдын *сүрөтүн же видеосун* жөнөт:\n\nФото болсо фото, видео болсо видео жөнөт - экөөн тең кабыл алам!", parse_mode="Markdown")
@dp.message(Add.media, F.photo)
async def add_media_photo(m: types.Message, state: FSMContext):
    await state.update_data(media_id=m.photo[-1].file_id, media_type="photo")
    await state.set_state(Add.price)
    await m.answer("💰 Баасын жаз:\nМисалы: 15000 сом")
@dp.message(Add.media, F.video)
async def add_media_video(m: types.Message, state: FSMContext):
    await state.update_data(media_id=m.video.file_id, media_type="video")
    await state.set_state(Add.price)
    await m.answer("🎥 Видео кабыл алынды ✅\n\n💰 Эми баасын жаз:\nМисалы: 15000 сом")
@dp.message(Add.media, F.video_note)
async def add_media_videonote(m: types.Message, state: FSMContext):
    await state.update_data(media_id=m.video_note.file_id, media_type="video")
    await state.set_state(Add.price)
    await m.answer("🎥 Видео кабыл алынды ✅\n\n💰 Эми баасын жаз:")
@dp.message(Add.media)
async def add_media_err(m: types.Message):
    await m.answer("Сураныч, сүрөт же видео жөнөт 📸🎥\nТекст эмес, фото/видео керек.")
@dp.message(Add.price)
async def add_price(m: types.Message, state: FSMContext):
    await state.update_data(price=m.text, price_num=parse_price(m.text))
    await state.set_state(Add.phone)
    kb = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="📱 Номеримди жөнөтүү", request_contact=True)]], resize_keyboard=True)
    await m.answer("📞 Телефон номериңди жаз же кнопканы бас:", reply_markup=kb)
@dp.message(Add.phone, F.contact)
async def add_phone_c(m: types.Message, state: FSMContext):
    await state.update_data(phone=m.contact.phone_number)
    await state.set_state(Add.city)
    await m.answer("🏙️ Шаар танда:", reply_markup=cities_kb())
@dp.message(Add.phone)
async def add_phone_t(m: types.Message, state: FSMContext):
    await state.update_data(phone=m.text)
    await state.set_state(Add.city)
    await m.answer("🏙️ Шаар танда:", reply_markup=cities_kb())
@dp.message(Add.city)
async def add_city(m: types.Message, state: FSMContext):
    city = m.text.replace("📍 ", "").replace("🌍 ", "")
    await state.update_data(city=city)
    await state.set_state(Add.location)
    await m.answer("📍 Так дарегиңди жаз:\nМисалы: Кызыл-Кыя, Фрунзе көчөсү")
@dp.message(Add.location)
async def add_loc(m: types.Message, state: FSMContext):
    await state.update_data(location=m.text)
    await state.set_state(Add.description)
    await m.answer("📝 Кошумча маалымат жаз:\nЖок болсо - деп жаз:")
@dp.message(Add.description)
async def add_desc(m: types.Message, state: FSMContext):
    d = await state.get_data()
    desc = "" if m.text == "-" else m.text
    user = f"@{m.from_user.username}" if m.from_user.username else m.from_user.full_name
    cur.execute("INSERT INTO listings (user_id, username, category, title, price, price_num, phone, location, city, description, photo_id, media_type, status) VALUES (?,?,?,?,?,?,?,?,?,?,?,?, 'active')", (m.from_user.id, user, d['category'], d['title'], d['price'], d.get('price_num',0), d['phone'], d['location'], d.get('city',''), desc, d.get('media_id',''), d.get('media_type','photo')))
    conn.commit(); lid = cur.lastrowid; await state.clear()
    cap = f"{d['category']}\n\n📌 {d['title']}\n💰 Баасы: {d['price']}\n🏙️ Шаар: {d.get('city','')}\n📍 Дареги: {d['location']}\n📞 Тел: {d['phone']}\n👤 Сатуучу: {user}\n📝 {desc}\n\n🆔 №{lid}"
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="✅ Сатылды деп белгилөө", callback_data=f"sold:{lid}")],[InlineKeyboardButton(text="🗑️ Өчүрүү", callback_data=f"del:{lid}")]])
    try:
        if d.get('media_type') == "video":
            await m.answer_video(video=d.get('media_id'), caption=cap, reply_markup=kb)
        else:
            await m.answer_photo(photo=d.get('media_id'), caption=cap, reply_markup=kb)
    except:
        await m.answer(cap, reply_markup=kb)
    await m.answer("✅ Жарыяң кошулду!", reply_markup=main_kb())
@dp.message(F.text == "🛒 Мал көрүү")
async def view_start(m: types.Message, state: FSMContext):
    await state.set_state(Browse.category)
    await m.answer("1️⃣ Кайсы малды көрөсүң?", reply_markup=cats_kb())
@dp.message(Browse.category)
async def b_cat(m: types.Message, state: FSMContext):
    if m.text == "⬅️ Артка":
        await state.clear(); await m.answer("Башкы меню", reply_markup=main_kb()); return
    if m.text not in CATEGORIES:
        await m.answer("Тизмеден танда 👇", reply_markup=cats_kb()); return
    await state.update_data(category=m.text)
    await state.set_state(Browse.city)
    await m.answer(f"2️⃣ {m.text} - Кайсы шаардан?", reply_markup=cities_kb())
@dp.message(Browse.city)
async def b_city(m: types.Message, state: FSMContext):
    if m.text == "⬅️ Артка":
        await state.set_state(Browse.category); await m.answer("Категория танда:", reply_markup=cats_kb()); return
    city = m.text.replace("📍 ", "").replace("🌍 ", "")
    await state.update_data(city=city)
    await state.set_state(Browse.price)
    await m.answer("3️⃣ Баасы канчага чейин?", reply_markup=prices_kb())
@dp.message(Browse.price)
async def b_price(m: types.Message, state: FSMContext):
    if m.text == "⬅️ Артка":
        await state.set_state(Browse.city); await m.answer("Шаар танда:", reply_markup=cities_kb()); return
    if m.text not in PRICES:
        await m.answer("Тизмеден танда 👇", reply_markup=prices_kb()); return
    d = await state.get_data()
    cat = d['category']; city = d.get('city','Баары')
    lo, hi = price_range(m.text)
    await state.clear()
    if city == "Баары":
        cur.execute("SELECT id, title, price, phone, location, city, description, photo_id, media_type, username, user_id FROM listings WHERE category=? AND status='active' AND price_num BETWEEN ? AND ? ORDER BY id DESC LIMIT 20", (cat, lo, hi))
    else:
        cur.execute("SELECT id, title, price, phone, location, city, description, photo_id, media_type, username, user_id FROM listings WHERE category=? AND status='active' AND city=? AND price_num BETWEEN ? AND ? ORDER BY id DESC LIMIT 20", (cat, city, lo, hi))
    rows = cur.fetchall()
    if not rows:
        await m.answer(f"😔 {cat} | {city} | {m.text} боюнча жарыя жок.", reply_markup=main_kb()); return
    await m.answer(f"✅ Табылды: {len(rows)} жарыя\n{cat} | 🏙️ {city} | {m.text}", reply_markup=main_kb())
    for r in rows:
        lid, title, price, phone, loc, cty, desc, media_id, media_type, user, owner = r
        await send_listing(m, cat, title, price, cty, loc, phone, user, desc, lid, media_id, media_type or "photo", is_owner=(owner == m.from_user.id))
@dp.callback_query(F.data.startswith("sold:"))
async def mark_sold(cb: types.CallbackQuery):
    lid = int(cb.data.split(":")[1])
    cur.execute("SELECT user_id, title FROM listings WHERE id=?", (lid,))
    row = cur.fetchone()
    if not row:
        await cb.answer("Табылган жок", show_alert=True); return
    if row[0] != cb.from_user.id:
        await cb.answer("Бул сенин жарыяң эмес!", show_alert=True); return
    cur.execute("UPDATE listings SET status='sold' WHERE id=?", (lid,))
    conn.commit()
    try:
        orig = cb.message.caption or cb.message.text or ""
        if cb.message.video or cb.message.photo:
            await cb.message.edit_caption(caption=orig + "\n\n❌ САТЫЛДЫ ✅", reply_markup=None)
        else:
            await cb.message.edit_text(text=orig + "\n\n❌ САТЫЛДЫ ✅", reply_markup=None)
    except:
        await cb.message.answer(f"✅ №{lid} САТЫЛДЫ деп белгиленди!")
    await cb.answer("✅ Сатылды!")
@dp.callback_query(F.data.startswith("del:"))
async def del_cb(cb: types.CallbackQuery):
    lid = int(cb.data.split(":")[1])
    cur.execute("DELETE FROM listings WHERE id=? AND user_id=?", (lid, cb.from_user.id))
    conn.commit()
    if cur.rowcount:
        await cb.message.answer(f"🗑️ №{lid} өчүрүлдү.")
        try: await cb.message.delete()
        except: pass
    await cb.answer()
@dp.message(F.text == "📋 Менин жарыяларым")
async def my_list(m: types.Message):
    cur.execute("SELECT id, category, title, price, city, status FROM listings WHERE user_id=? ORDER BY id DESC", (m.from_user.id,))
    rows = cur.fetchall()
    if not rows:
        await m.answer("Сенде азырынча жарыя жок."); return
    for r in rows:
        lid, cat, title, price, city, status = r
        em = "✅ Активдүү" if status == "active" else "❌ САТЫЛДЫ"
        txt = f"{cat}\n📌 {title}\n💰 {price}\n🏙️ {city}\nСтатус: {em}\n🆔 №{lid}"
        if status == "active":
            kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="✅ Сатылды", callback_data=f"sold:{lid}")],[InlineKeyboardButton(text="🗑️ Өчүрүү", callback_data=f"del:{lid}")]])
        else:
            kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🗑️ Өчүрүү", callback_data=f"del:{lid}")]])
        await m.answer(txt, reply_markup=kb)
async def main():
    print("Bot ishtep jatat...")
    await dp.start_polling(bot)
if __name__ == "__main__":
    asyncio.run(main())
