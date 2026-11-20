# ABU BOT

Telegram ekotizimi: bot, Mini App (kabinet, 3D ABU F tanga va ABU TON olmos), do‘kon (Premium, Stars, sovg‘alar, kolleksiya), bozor, vazifalar, promo-kodlar, kunlik bonus, VIP, yutuqlar va veb admin panel.

[![CI](https://github.com/OWNER/abu-bot/actions/workflows/ci.yml/badge.svg)](https://github.com/OWNER/abu-bot/actions)

## Loyiha tuzilishi
- `app/bot/` — Telegram bot: handlerlar, menyu, middleware
- `app/services/` — biznes mantiq: hamyon, do‘kon, bozor, vazifa, promo, yutuq, emoji
- `app/db/` — SQLAlchemy modellari va sessiya
- `app/api/` — Mini App va admin API
- `static/` — Mini App (`/app`) va admin panel (`/admin`)
- `migrations/` — Alembic migratsiyalari
- `tests/` — avtomatik testlar (GitHub Actions'da ham ishlaydi)

## GitHub'ga yuklash
1. Repozitoriy yarating, ZIP'ni oching va fayllarni yuklang (yoki `git init && git add . && git commit -m "ABU BOT"`).
2. Repozitoriy Settings → Secrets emas, Render Environment'da maxfiy kalitlarni saqlang. `.env` GitHub'ga yuklanmaydi (`.gitignore` bilan himoyalangan).
3. `main` ga push qilinganda CI testlarni avtomatik ishga tushiradi.



## Hozir nima tayyor
- Telegram bot: `/start`, ro‘yxatdan o‘tish, noyob ABU ID, til tanlash (uz/ru/en), majburiy kanal obunasi, asosiy menyu
- Ishlaydigan bo‘limlar: 👤 Kabinet, 💎 Valyutalar, 👥 Referallar, 🏆 Reyting, ⚙️ Sozlamalar, ❓ Yordam
- Ikki valyuta hisobi: ABU F va ABU TON (atomik amallar, to‘liq tarix, manfiy balansga yo‘l qo‘yilmaydi, takroriy amaldan himoya)
- Markazlashgan Premium Custom Emoji tizimi (admin buyruqlari orqali)
- Admin: kanal qo‘shish/o‘chirish, balansni tuzatish (audit jurnali bilan)
- Do‘kon (🛍 🎁 🎨): Telegram Premium, Stars bilan to‘ldirish, Telegram sovg‘alari, Collectible, NFT, maxsus mahsulotlar
- To‘lov: Stars (rasmiy invoice, XTR) yoki ABU F / ABU TON; buyurtma holatlari, takroriy to‘lovdan himoya, oshib sotilishdan himoya, xato bo‘lsa avtomatik qaytarish
- Admin: /product_list, /product_add, /product_meta, /product_toggle, /gifts_sync, /refund
- Ma’lumotlar bazasi modellari: foydalanuvchi, hamyon, tranzaksiya, emoji, kanal, audit, mahsulot, buyurtma, to‘lov

## Hali tayyor EMAS (keyingi bosqichlar)
## Vazifalar va promo-kodlar (4-bosqich)
- 📋 Vazifalar: kunlik (har kuni qayta bajariladi), bir martalik, kanalga obuna (bot haqiqiy a’zolikni tekshiradi), referal vazifasi.
- 🎟 Promo-kod: foydalanuvchi `/promo KOD` yuboradi. Limit, muddat va «bir foydalanuvchiga bir marta» qoidasi bazada tekshiriladi.
- Admin: `/task_add`, `/promo_add`, `/promo_off`.

## Mini App (3-bosqich)
- Manzil: `https://SIZNING-DOMEN/app` — BotFather'da Web App sifatida ulang.
- Kabinet: ABU ID, ABU F va ABU TON balanslari, daraja/XP, streak, takliflar, tarix, buyurtmalar, kolleksiya, banner karuseli.
- 3D ABU F tanga (aylanadi) va ABU TON olmos (SVG gradient, tebranadi). Harakat «kamaytirilgan harakat» sozlamasida o‘chadi.
- Xavfsizlik: server Telegram initData imzosini HMAC bilan tekshiradi; mijoz yuborgan ID yoki balansga ishonilmaydi.

vazifalar, promo-kodlar, bozor (foydalanuvchilar o‘rtasida), kunlik bonus/streak, VIP, yutuqlar, banner karuseli, to‘liq veb admin panel. 📋 🎟 tugmalari hozir «keyingi bosqichda» xabarini beradi.

## Premium, Stars, Sovg‘alar, NFT: cheklovlar (ochiq aytamiz)
- **Stars** to‘lovi to‘liq rasmiy. Foydalanuvchi Stars to‘laydi → ABU F oladi (Stars to‘ldirish).
- **Premium va Telegram sovg‘alari** botning O‘ZINING Stars balansidan to‘lanadi. Bot egasi balansni to‘ldirib turishi shart. Sovg‘a hozircha xaridorning o‘ziga yuboriladi. Premium uchun yangi aiogram versiyasi kerak; eskirgan bo‘lsa, buyurtma bajarilmaydi va pul qaytariladi.
- **Collectible va NFT** — ABU BOT ichidagi raqamli kolleksiya (seriya raqami bilan). Telegram'dagi haqiqiy Collectible Gift'larni bot orqali sotib olish/o‘tkazish rasmiy API orqali bu versiyada ulanmagan.
- Narxlar boshlang‘ich (sinov) qiymatlar; admin o‘zgartiradi.
- Hozircha faqat testlarning emoji qismi ishga tushirib ko‘rilgan; bot Telegram'ga ulanib sinalgani yo‘q.

## Ishga tushirish (lokal)
0. Bazani yangilash: `alembic upgrade head` (birinchi marta jadvallarni yaratadi)
1. `pip install -r requirements.txt`
2. `.env.example` ni `.env` ga nusxalang, `BOT_TOKEN` (@BotFather'dan) va `ADMIN_IDS` (o‘z Telegram ID'ingiz) ni yozing
3. `python run_polling.py`

## Render'ga joylash
1. Loyihani GitHub'ga yuklang, Render'da «New → Blueprint» tanlab `render.yaml` ni ulang
2. `BOT_TOKEN`, `BOT_USERNAME`, `ADMIN_IDS`, `WEBHOOK_BASE_URL` (Render bergan https manzil) ni kiriting
3. Faqat 1 ta worker ishlatiladi (`--workers 1`)

## Emoji sozlamalari (admin)
`/admin` yozing. Asosiy: `/emoji_set ❤️ <ID>`, `/emoji_list`, `/emoji_remove`, `/emoji_reset`, `/emoji_test`, `/emoji_export`, `/emoji_import`.
Cheklovlar: tugma (menyu) yozuvlarida va ba’zi joylarda Telegram Custom Emoji'ni qo‘llamaydi; faqat matnli xabarlarda ishlaydi. Telegram botlarga Custom Emoji ruxsatini alohida shartlar bilan beradi — ishlamasa, bot avtomatik oddiy emojiga qaytadi.

## Testlar
`python -m unittest discover tests`

## Muhim sozlamalar (Render → Environment)
- `BOT_TOKEN`, `BOT_USERNAME`, `ADMIN_IDS`, `WEBHOOK_BASE_URL`, `WEBHOOK_SECRET`
- `ADMIN_PANEL_TOKEN` (kamida 24 belgi): veb admin paneli kaliti, `/admin`
- `MARKET_FEE_PERCENT` (standart 5), `REFERRAL_BONUS_ABU_F` (standart 50)

## Sizning tomoningizdan qilinadigan ishlar
1. BotFather: bot yarating, `/setmenubutton` orqali Mini App manzilini `/app` ga bog‘lang.
2. Majburiy kanallar uchun botni kanalga admin qiling, so‘ng `/channel_add @kanal`.
3. Telegram Stars: bot hisobini to‘ldiring (Premium va sovg‘alar shu balansdan to‘lanadi).
4. Custom Emoji ishlashi uchun Telegram talablarini tekshiring; ID'larni `/emoji_set` bilan kiriting.
5. Haqiqiy foydalanuvchi bilan sinov: ro‘yxatdan o‘tish, to‘lov, bozor, promo, admin panel.

## Ma’lum cheklovlar
- Telegram'dagi haqiqiy Collectible Gift'larni sotish yoki o‘tkazish bot orqali rasmiy qo‘llab-quvvatlanmaydi. Bu ABU BOT ichidagi raqamli kolleksiya sifatida ishlaydi.
- Premium va sovg‘alar botning Stars balansidan to‘lanadi.
- Admin paneldagi amallar hozircha umumiy «veb» belgisi bilan yoziladi; alohida administrator identifikatsiyasi keyingi versiyada.
- 3D tanga va olmos SVG/CSS orqali; fotorealistik model uchun dizayner aktivi kerak.
- Loyiha sinovdan o‘tkazilmagan holda topshirilmoqda: birinchi ishga tushirishda xatolar bo‘lishi mumkin.
