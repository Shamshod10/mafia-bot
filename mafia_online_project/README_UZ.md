# MAFIA ONLINE — boshlang‘ich ishlaydigan loyiha

Telegram bot + Mini App uchun MVP. Python, aiogram 3, FastAPI, SQLite va oddiy HTML/CSS/JS ishlatiladi.

## 1. Kerakli narsalar
- Python 3.11 yoki yangiroq
- VS Code
- Telegram'da @BotFather orqali yaratilgan bot tokeni
- Mini Appni Telegram ichida ochish uchun HTTPS bilan ochiq turgan manzil (masalan, o‘zingizning serveringiz yoki tunnel)

## 2. O‘rnatish (Windows PowerShell)
Loyiha papkasini VS Code'da oching, Terminal → New Terminal:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
```

`.env` faylini ochib `BOT_TOKEN` va `WEBAPP_URL` qiymatlarini o‘zgartiring. Bot tokenini hech kimga yubormang.

PowerShell'da `.env` avtomatik o‘qilmaydi. Ishga tushirishdan oldin joriy terminalda qiymatlarni kiriting:

```powershell
$env:BOT_TOKEN="BOTFATHER_BERGAN_TOKEN"
$env:WEBAPP_URL="https://SIZNING-HTTPS-MANZILINGIZ"
python main.py
```

API va sayt `http://127.0.0.1:8000` manzilida ishlaydi. Sog‘liq tekshiruvi: `http://127.0.0.1:8000/api/health`.

## 3. Telegram sozlamasi
1. Telegram'da @BotFather → `/newbot` orqali bot yarating.
2. Tokenni terminaldagi `BOT_TOKEN` ga kiriting.
3. Mini App tugmasi ishlashi uchun `WEBAPP_URL` HTTPS manzil bo‘lishi kerak. `https://example.com` faqat namuna — uni o‘zingizning manzilingizga almashtiring.
4. Botga `/start` yuboring va Mini App tugmasini bosing.

## 4. Birinchi test
- Mini Appni oching.
- O‘yinchi nomini kiriting va xona yarating.
- Do‘stlar qo‘shilishi uchun ularga ham saytning HTTPS manzili va xona kodini bering.
- Kamida 5 ta o‘yinchi bilan boshlash mumkin. Lokal brauzerda test rejimida foydalanuvchi ID avtomatik yaratiladi.

## 5. Muhim MVP cheklovlari
Bu birinchi prototip: xona yaratish/qo‘shilish, rol tarqatish, kunduzgi chat, ovoz berish va bosqichni xona egasi almashtirishi mavjud. Hozircha tungi harakatlarni avtomatik yechish, taymer, g‘alabani hisoblash, admin panel, real Telegram `initData` imzosini serverda tekshirish va ishlab chiqarish darajasidagi himoya to‘liq qo‘shilmagan. Shuning uchun uni ommaga chiqarishdan oldin bu qismlarni yakunlash kerak.

**Xavfsizlik:** hozirgi versiyada brauzer yuborgan `telegram_id` serverda haqiqiy Telegram foydalanuvchisi ekanini isbotlamaydi. Faqat test uchun ishlating. Public serverga joylashdan oldin Telegram Mini App `initData` tekshiruvini server tomonda qo‘shing va API ruxsatlarini kuchaytiring.
