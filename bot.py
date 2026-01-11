import os
import logging
from datetime import datetime
from typing import Optional
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types
from aiogram.dispatcher.filters import Command
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import qrcode
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
import cv2
from pyzbar.pyzbar import decode
import json

load_dotenv()

logging.basicConfig(level=logging.INFO)

bot = Bot(token=os.getenv("BOT_TOKEN"))
dp = Dispatcher()

ADMIN_ID = int(os.getenv("ADMIN_ID"))

class CouponStates(StatesGroup):
    waiting_for_recipient = State()
    waiting_for_count = State()
    waiting_for_expiry = State()
    waiting_for_delete = State()

COUPONS_FILE = "coupons.json"
USED_FILE = "used_coupons.json"
CNTR_FILE = "counters.json"

def load_coupons() -> dict:
    """Load coupons from JSON file"""
    if os.path.exists(COUPONS_FILE):
        try:
            with open(COUPONS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError:
            return {}
    return {}

def load_used() -> dict:
    """Load used coupons from JSON file"""
    if os.path.exists(USED_FILE):
        try:
            with open(USED_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError:
            return {}
    return {}

def load_cntrs() -> dict:
    """Load counters from JSON file"""
    if os.path.exists(CNTR_FILE):
        try:
            with open(CNTR_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError:
            return {}
    return {}

def save_coupons(coupons: dict):
    """Save coupons to JSON file"""
    with open(COUPONS_FILE, 'w', encoding='utf-8') as f:
        json.dump(coupons, f, ensure_ascii=False, indent=4)

def save_used(used: dict):
    """Save used coupons to JSON file"""
    with open(USED_FILE, 'w', encoding='utf-8') as f:
        json.dump(used, f, ensure_ascii=False, indent=4)

def save_cntrs(cntrs: dict):
    """Save counters to JSON file"""
    with open(CNTR_FILE, 'w', encoding='utf-8') as f:
        json.dump(cntrs, f, ensure_ascii=False, indent=4)

coupons = load_coupons()
used = load_used()
cntrs = load_cntrs()

def get_admin_kb() -> ReplyKeyboardMarkup:
    """Create admin keyboard"""
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📝 Создать купон"), KeyboardButton(text="📊 Статистика")],
            [KeyboardButton(text="📋 Список купонов"), KeyboardButton(text="🔍 Сканировать QR")],
            [KeyboardButton(text="📜 История использованных"), KeyboardButton(text="🗑 Удалить купон")]
        ],
        resize_keyboard=True
    )
    return kb

def get_user_kb() -> ReplyKeyboardMarkup:
    """Create user keyboard"""
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🎫 Мои купоны")]
        ],
        resize_keyboard=True
    )
    return kb

def gen_coupon_id() -> str:
    """Generate a unique coupon ID"""
    import random
    import string
    chars = string.ascii_uppercase + string.digits
    return f"PROMO-{''.join(random.choices(chars, k=6))}"

def gen_qr(cid: str) -> str:
    """Generate QR code for coupon and return path to saved image"""
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(cid)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    fname = f"qr_{cid}.png"
    img.save(fname)
    return fname

def create_pdf(coupons: list) -> str:
    """Create PDF with multiple coupons"""
    fname = f"coupons_{coupons[0]['recipient']}.pdf"
    c = canvas.Canvas(fname, pagesize=A4)
    w, h = A4

    for i, cpn in enumerate(coupons):
        c.setFillColorRGB(0.95, 0.95, 0.95)
        c.rect(0, 0, w, h, fill=True)

        c.setStrokeColorRGB(0.2, 0.2, 0.2)
        c.setLineWidth(2)
        c.rect(20*mm, 20*mm, w - 40*mm, h - 40*mm)

        c.setFillColorRGB(0.2, 0.2, 0.2)
        c.setFont("Helvetica-Bold", 32)
        c.drawCentredString(w/2, h - 60*mm, "КУПОН")

        c.setFont("Helvetica-Bold", 20)
        c.drawCentredString(w/2, h - 90*mm, f"Для: {cpn['recipient']}")

        c.setFont("Helvetica-Bold", 18)
        c.drawCentredString(w/2, h - 120*mm, f"Купон #{i+1} из {len(coupons)}")

        c.setFont("Helvetica-Bold", 18)
        c.drawCentredString(w/2, h - 150*mm, f"Код: {cpn['coupon_id']}")

        c.setFont("Helvetica", 16)
        c.drawCentredString(w/2, h - 180*mm, f"Действует до: {cpn['expiry_date']}")

        qr_path = gen_qr(cpn["coupon_id"])
        c.drawImage(qr_path, w/2 - 35*mm, h - 260*mm, width=70*mm, height=70*mm)
        os.remove(qr_path)

        c.setFont("Helvetica", 12)
        c.drawCentredString(w/2, 40*mm, "Покажите этот купон при оплате")
        c.drawCentredString(w/2, 30*mm, "Одноразовое использование")

        c.setFont("Helvetica", 10)
        c.drawCentredString(w/2, 20*mm, f"Страница {i+1} из {len(coupons)}")

        if i < len(coupons) - 1:
            c.showPage()

    c.save()
    return fname

@dp.message(Command("start"))
async def cmd_start(msg: Message):
    """Handle /start command"""
    if msg.from_user.id == ADMIN_ID:
        await msg.answer(
            "👋 Добро пожаловать в панель администратора!\n\n"
            "Выберите действие из меню ниже:",
            reply_markup=get_admin_kb()
        )
    else:
        await msg.answer(
            "👋 Привет! Я бот для работы с купонами.\n\n"
            "Используйте меню ниже для навигации:",
            reply_markup=get_user_kb()
        )

@dp.message(lambda msg: msg.text == "📝 Создать купон")
async def create_coupon_btn(msg: Message, state: FSMContext):
    """Handle create coupon button"""
    if msg.from_user.id != ADMIN_ID:
        await msg.answer("⛔️ У вас нет доступа к этой функции.")
        return

    await state.set_state(CouponStates.waiting_for_recipient)
    await msg.answer("Введите имя получателя купона:")

@dp.message(CouponStates.waiting_for_recipient)
async def process_recipient(msg: Message, state: FSMContext):
    """Process recipient name and ask for coupon count"""
    await state.update_data(recipient=msg.text)
    await state.set_state(CouponStates.waiting_for_count)
    await msg.answer("Введите количество купонов для генерации (от 1 до 10):")

@dp.message(CouponStates.waiting_for_count)
async def process_count(msg: Message, state: FSMContext):
    """Process coupon count and ask for expiry date"""
    try:
        cnt = int(msg.text)
        if cnt < 1 or cnt > 10:
            await msg.answer("❌ Количество должно быть от 1 до 10. Попробуйте снова:")
            return
        await state.update_data(count=cnt)
        await state.set_state(CouponStates.waiting_for_expiry)
        await msg.answer("Введите дату окончания действия (ДД.ММ.ГГГГ):")
    except ValueError:
        await msg.answer("❌ Пожалуйста, введите число от 1 до 10:")

@dp.message(CouponStates.waiting_for_expiry)
async def process_expiry(msg: Message, state: FSMContext):
    """Process expiry date and create coupons"""
    try:
        exp_date = datetime.strptime(msg.text, "%d.%m.%Y")
        if exp_date < datetime.now():
            await msg.answer("❌ Дата окончания не может быть в прошлом. Попробуйте снова:")
            return

        data = await state.get_data()
        cnt = data["count"]
        rcpt = data["recipient"]

        cpn_data = []
        for i in range(cnt):
            cid = gen_coupon_id()
            cpn = {
                "coupon_id": cid,
                "recipient": rcpt,
                "expiry_date": msg.text,
                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "used": False
            }
            cpn_data.append(cpn)
            coupons[cid] = cpn
            save_coupons(coupons)

        pdf_path = create_pdf(cpn_data)

        await msg.answer(
            f"✅ Создано {cnt} купонов для {rcpt}!\n\n"
            f"👤 Получатель: {rcpt}\n"
            f"📅 Срок действия: до {msg.text}\n"
            "⚠️ Покажите PDF-файл с QR-кодом при использовании\n"
            "🔁 Одноразовые купоны"
        )
        await msg.answer_document(types.FSInputFile(pdf_path))

        os.remove(pdf_path)
        await state.clear()

    except ValueError:
        await msg.answer("❌ Неверный формат даты. Используйте формат ДД.ММ.ГГГГ:")

@dp.message(lambda msg: msg.text == "📊 Статистика")
async def show_stats(msg: Message):
    """Show detailed coupon statistics"""
    if msg.from_user.id != ADMIN_ID:
        await msg.answer("⛔️ У вас нет доступа к этой функции.")
        return

    total = len(coupons)
    used_cnt = sum(1 for c in coupons.values() if c["used"])
    active = sum(1 for c in coupons.values() if not c["used"])
    expired = sum(
        1
        for c in coupons.values()
        if datetime.strptime(c["expiry_date"], "%d.%m.%Y") < datetime.now()
    )

    usr_stats = {}
    for cpn in coupons.values():
        rcpt = cpn["recipient"]
        if rcpt not in usr_stats:
            usr_stats[rcpt] = {"active": 0, "used": 0, "expired": 0}

        if cpn["used"]:
            usr_stats[rcpt]["used"] += 1
        elif datetime.strptime(cpn["expiry_date"], "%d.%m.%Y") < datetime.now():
            usr_stats[rcpt]["expired"] += 1
        else:
            usr_stats[rcpt]["active"] += 1

    stats = (
        "📊 Детальная статистика купонов:\n\n"
        f"📦 Всего купонов в системе: {total}\n"
        f"✅ Активных: {active}\n"
        f"❌ Использованных: {used_cnt}\n"
        f"⏰ Истекших: {expired}\n\n"
        "👥 Статистика по пользователям:\n"
    )

    for rcpt, data in usr_stats.items():
        total_usr = sum(data.values())
        stats += (
            f"\n👤 {rcpt}:\n"
            f"   📦 Всего купонов: {total_usr}\n"
            f"   ✅ Активных: {data['active']}\n"
            f"   ❌ Использованных: {data['used']}\n"
            f"   ⏰ Истекших: {data['expired']}\n"
        )

    last_24h = sum(
        1
        for c in used.values()
        if (datetime.now() - datetime.strptime(c["used_at"], "%Y-%m-%d %H:%M:%S")).total_seconds()
        < 86400
    )

    stats += f"\n📈 Использовано за последние 24 часа: {last_24h}"

    await msg.answer(stats)

@dp.message(lambda msg: msg.text == "📋 Список купонов")
async def list_coupons_btn(msg: Message, state: FSMContext):
    """Handle list coupons button"""
    if msg.from_user.id != ADMIN_ID:
        await msg.answer("⛔️ У вас нет доступа к этой функции.")
        return

    await msg.answer("👤 Введите имя получателя для просмотра купонов:")

@dp.message(lambda msg: msg.text and msg.from_user.id == ADMIN_ID)
async def process_recipient_name(msg: Message):
    """Process recipient name for coupon listing"""
    rcpt = msg.text
    active = [c for c in coupons.values() if c["recipient"] == rcpt]
    used_cpns = [c for c in used.values() if c["recipient"] == rcpt]

    used_cnt = cntrs.get(rcpt, 0)

    if not active and not used_cpns:
        await msg.answer(
            f"📭 Купоны для {rcpt} не найдены.",
            reply_markup=get_admin_kb()
        )
        return

    resp = f"📋 Купоны для {rcpt}:\n\n"

    if active:
        exp_date = active[0]["expiry_date"]
        resp += (
            f"✅ Активные купоны: {len(active)}\n"
            f"📅 Срок действия: до {exp_date}\n\n"
        )
        for cpn in active:
            resp += f"🆔 {cpn['coupon_id']}\n"
        resp += "\n"

    resp += f"❌ Всего использовано купонов: {used_cnt}\n"
    if used_cpns:
        resp += f"📜 Последние использованные:\n"
        for cpn in used_cpns[-5:]:
            resp += (
                f"🆔 {cpn['coupon_id']}\n"
                f"📅 Использован: {cpn['used_at']}\n"
            )

    await msg.answer(resp, reply_markup=get_admin_kb())

@dp.message(lambda msg: msg.text == "📜 История использованных")
async def show_used_history(msg: Message):
    """Show history of used coupons"""
    if msg.from_user.id != ADMIN_ID:
        await msg.answer("⛔️ У вас нет доступа к этой функции.")
        return

    if not used:
        await msg.answer("📭 История использованных купонов пуста.")
        return

    rcpts = {}
    for cpn in used.values():
        if cpn["recipient"] not in rcpts:
            rcpts[cpn["recipient"]] = []
        rcpts[cpn["recipient"]].append(cpn)

    resp = "📜 История использованных купонов:\n\n"
    for rcpt, cpns in rcpts.items():
        resp += f"👤 {rcpt}:\n"
        for cpn in cpns:
            resp += (
                f"🆔 {cpn['coupon_id']}\n"
                f"📅 Использован: {cpn['used_at']}\n"
                f"📅 Срок действия был до: {cpn['expiry_date']}\n\n"
            )

    await msg.answer(resp)

@dp.message(lambda msg: msg.text == "🔍 Сканировать QR")
async def scan_qr_btn(msg: Message):
    """Handle scan QR button"""
    if msg.from_user.id != ADMIN_ID:
        await msg.answer("⛔️ У вас нет доступа к этой функции.")
        return

    await msg.answer(
        "📸 Отправьте четкое фото QR-кода для сканирования.\n\n"
        "⚠️ Важно:\n"
        "• Убедитесь, что QR-код хорошо освещен\n"
        "• Фото должно быть четким и без бликов\n"
        "• QR-код должен занимать большую часть кадра"
    )

@dp.message(lambda msg: msg.photo is not None)
async def process_qr(msg: Message):
    """Process QR code from photo"""
    if msg.from_user.id != ADMIN_ID:
        await msg.answer("⛔️ Только администратор может сканировать QR-коды.")
        return

    try:
        file = await bot.get_file(msg.photo[-1].file_id)
        fpath = f"temp_{msg.message_id}.jpg"
        await bot.download_file(file.file_path, fpath)

        img = cv2.imread(fpath)
        if img is None:
            await msg.answer("❌ Ошибка при чтении изображения. Попробуйте еще раз.")
            return

        decoded = decode(img)

        os.remove(fpath)

        if not decoded:
            await msg.answer(
                "❌ QR-код не найден на изображении.\n\n"
                "Возможные причины:\n"
                "• Нечеткое изображение\n"
                "• Плохое освещение\n"
                "• QR-код поврежден\n\n"
                "Попробуйте сделать фото еще раз."
            )
            return

        cid = decoded[0].data.decode()

        if not cid.startswith("PROMO-"):
            await msg.answer("❌ Неверный формат QR-кода. Это не купон.")
            return

        if cid not in coupons:
            await msg.answer(
                "❌ Купон не найден в базе данных.\n\n"
                "Возможные причины:\n"
                "• Купон уже использован\n"
                "• Купон был удален\n"
                "• QR-код поврежден"
            )
            return

        cpn = coupons[cid]
        exp_date = datetime.strptime(cpn["expiry_date"], "%d.%m.%Y")

        if exp_date < datetime.now():
            await msg.answer(
                f"❌ Срок действия купона истек.\n\n"
                f"👤 Получатель: {cpn['recipient']}\n"
                f"📅 Срок действия был до: {cpn['expiry_date']}"
            )
            return

        if cpn["used"]:
            await msg.answer(
                "❌ Этот купон уже был использован.\n\n"
                f"👤 Получатель: {cpn['recipient']}\n"
                f"🆔 ID: {cpn['coupon_id']}\n"
                f"📅 Действует до: {cpn['expiry_date']}"
            )
            return
        rcpt = cpn["recipient"]
        cntrs[rcpt] = cntrs.get(rcpt, 0) + 1
        save_cntrs(cntrs)

        used_cpn = cpn.copy()
        used_cpn["used_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        used[cid] = used_cpn
        save_used(used)

        del coupons[cid]
        save_coupons(coupons)

        await msg.answer(
            f"✅ Купон успешно активирован!\n\n"
            f"👤 Получатель: {cpn['recipient']}\n"
            f"🆔 ID: {cpn['coupon_id']}\n"
            f"📅 Действует до: {cpn['expiry_date']}\n"
            f"⏰ Использован: {used_cpn['used_at']}\n"
            f"📊 Всего использовано купонов: {cntrs[rcpt]}\n\n"
            "✅ Купон помечен как использованный и удален из базы.",
            reply_markup=get_admin_kb()
        )

        logging.info(f"Coupon {cid} used by {rcpt} at {used_cpn['used_at']}")

    except Exception as e:
        logging.error(f"Error processing QR code: {str(e)}")
        await msg.answer(
            "❌ Произошла ошибка при обработке QR-кода.\n"
            "Пожалуйста, попробуйте еще раз или обратитесь к администратору."
        )

@dp.message(lambda msg: msg.text == "🎫 Мои купоны")
async def my_coupons_btn(msg: Message):
    usr_cpns = [c for c in coupons.values() if c.get("user_id") == msg.from_user.id]
    if not usr_cpns:
        await msg.answer("📭 У вас пока нет купонов.")
        return

    resp = "🎫 Ваши купоны:\n\n"
    for cpn in usr_cpns:
        status = "✅ Активен" if not cpn["used"] else "❌ Использован"
        if datetime.strptime(cpn["expiry_date"], "%d.%m.%Y") < datetime.now():
            status = "⏰ Истек"
        resp += (
            f"🆔 {cpn['coupon_id']}\n"
            f"📅 Действует до: {cpn['expiry_date']}\n"
            f"📊 Статус: {status}\n\n"
        )
    await msg.answer(resp)

@dp.message(lambda msg: msg.text == "🗑 Удалить купон")
async def delete_coupon_btn(msg: Message, state: FSMContext):
    if msg.from_user.id != ADMIN_ID:
        await msg.answer("⛔️ У вас нет доступа к этой функции.")
        return
    if not coupons:
        await msg.answer("📭 Список купонов пуст.")
        return

    await state.set_state(CouponStates.waiting_for_delete)
    await msg.answer("👤 Введите имя пользователя, у которого нужно удалить купоны:")

@dp.message(CouponStates.waiting_for_delete)
async def process_delete_coupons(msg: Message, state: FSMContext):
    """Process coupon deletion by username and count"""
    rcpt = msg.text
    usr_cpns = [c for c in coupons.values() if c["recipient"] == rcpt]

    if not usr_cpns:
        await msg.answer(f"📭 Купоны для пользователя {rcpt} не найдены.")
        await state.clear()
        return

    await state.update_data(delete_recipient=rcpt)
    await msg.answer(
        f"👤 Пользователь: {rcpt}\n"
        f"📦 Доступно купонов: {len(usr_cpns)}\n\n"
        "Введите количество купонов для удаления:"
    )
    await state.set_state(CouponStates.waiting_for_count)

@dp.message(CouponStates.waiting_for_count)
async def process_delete_count(msg: Message, state: FSMContext):
    """Process number of coupons to delete"""
    try:
        cnt = int(msg.text)
        data = await state.get_data()
        rcpt = data["delete_recipient"]
        usr_cpns = [c for c in coupons.values() if c["recipient"] == rcpt]

        if cnt < 1:
            await msg.answer("❌ Количество должно быть больше 0. Попробуйте снова:")
            return

        if cnt > len(usr_cpns):
            await msg.answer(f"❌ У пользователя {rcpt} только {len(usr_cpns)} купонов. Попробуйте снова:")
            return

        del_cnt = 0
        for cpn in usr_cpns[:cnt]:
            cid = cpn["coupon_id"]
            del coupons[cid]
            del_cnt += 1

        save_coupons(coupons)

        await msg.answer(
            f"✅ Успешно удалено {del_cnt} купонов у пользователя {rcpt}!\n"
            f"📦 Осталось купонов: {len(usr_cpns) - del_cnt}",
            reply_markup=get_admin_kb()
        )
        await state.clear()

    except ValueError:
        await msg.answer("❌ Пожалуйста, введите число:")

async def main():
    """Start the bot"""
    await dp.start_polling(bot)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())

