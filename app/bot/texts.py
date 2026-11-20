LANGS = {"uz": "🇺🇿 O‘zbekcha", "ru": "🇷🇺 Русский", "en": "🇬🇧 English"}
MENU_KEYS = ["cabinet", "shop", "currencies", "gifts", "nft", "tasks", "promo",
             "referrals", "rating", "settings", "help"]
MENU_LAYOUT = [["cabinet", "shop"], ["currencies", "gifts"], ["nft", "tasks"],
               ["promo", "referrals"], ["rating", "settings"], ["help"]]

T = {
    "uz": {
        "menu.cabinet": "👤 Kabinet", "menu.shop": "🛍 Do‘kon", "menu.currencies": "💎 Valyutalar",
        "menu.gifts": "🎁 Sovg‘alar", "menu.nft": "🎨 NFT va Collectibles", "menu.tasks": "📋 Vazifalar",
        "menu.promo": "🎟 Promo-kod", "menu.referrals": "👥 Referallar", "menu.rating": "🏆 Reyting",
        "menu.settings": "⚙️ Sozlamalar", "menu.help": "❓ Yordam",
        "choose_lang": "🌐 Tilni tanlang / Выберите язык / Choose language",
        "welcome": "🎉 <b>ABU BOT</b> ga xush kelibsiz, {name}!\n🆔 Sizning ABU ID: <code>{abu_id}</code>\n\nQuyidagi menyudan bo‘limni tanlang.",
        "welcome_back": "🌟 Qaytganingiz bilan, {name}! Menyudan bo‘limni tanlang.",
        "must_sub": "⚠️ Davom etish uchun quyidagi kanallarga obuna bo‘ling, so‘ng «Tekshirish» tugmasini bosing.",
        "check_sub": "✅ Tekshirish", "still_missing": "❌ Hali hamma kanalga obuna bo‘lmagansiz.",
        "start_first": "ℹ️ Avval /start buyrug‘ini yuboring.",
        "cabinet": ("👤 <b>{name}</b> {username}\n🆔 ABU ID: <code>{abu_id}</code>\n\n"
                    "🪙 ABU F: <b>{abu_f}</b>\n💎 ABU TON: <b>{abu_ton}</b>\n\n"
                    "👑 VIP: {vip}\n📈 Daraja: {level}\n{bar} {xp} XP\n🔥 Streak: {streak} kun\n"
                    "👥 Takliflar: {refs}"),
        "vip_yes": "faol ({until})", "vip_no": "yo‘q",
        "currencies": ("💎 <b>Valyutalar</b>\n\n🪙 <b>ABU F</b> (oltin tanga): <b>{abu_f}</b>\n"
                       "💎 <b>ABU TON</b> (olmos): <b>{abu_ton}</b>\n\n<b>So‘nggi amallar:</b>\n{tx}"),
        "no_tx": "Hozircha amallar yo‘q.",
        "referrals": ("👥 <b>Referallar</b>\n\nTaklif qilganlar: <b>{count}</b>\n"
                      "Har bir do‘st uchun: <b>{bonus} ABU F</b>\n\n🔗 Sizning havolangiz:\n{link}"),
        "rating": "🏆 <b>Reyting (XP bo‘yicha)</b>\n\n{rows}",
        "settings": "⚙️ <b>Sozlamalar</b>\n\n🌐 Tilni tanlang:",
        "lang_set": "✅ Til o‘zgartirildi.",
        "help": ("❓ <b>Yordam</b>\n\n/start — asosiy menyu\n/daily — kunlik bonus\n/vip — VIP obuna\n/achievements — yutuqlar\n/promo KOD — promo-kod\n/market — bozor, /sell, /buy, /cancel_listing\n👤 Kabinet — profil va balans\n"
                 "💎 Valyutalar — ABU F va ABU TON\n👥 Referallar — do‘stlarni taklif qilish\n"
                 "Muammo bo‘lsa, administratorga murojaat qiling."),
        "pending": "ℹ️ Bu bo‘lim hali ishga tushirilmagan (keyingi bosqichda qo‘shiladi).",
        "error": "⚠️ Xatolik yuz berdi. Iltimos, birozdan so‘ng qayta urinib ko‘ring.",
    },
    "ru": {
        "menu.cabinet": "👤 Кабинет", "menu.shop": "🛍 Магазин", "menu.currencies": "💎 Валюты",
        "menu.gifts": "🎁 Подарки", "menu.nft": "🎨 NFT и Collectibles", "menu.tasks": "📋 Задания",
        "menu.promo": "🎟 Промокод", "menu.referrals": "👥 Рефералы", "menu.rating": "🏆 Рейтинг",
        "menu.settings": "⚙️ Настройки", "menu.help": "❓ Помощь",
        "welcome": "🎉 Добро пожаловать в <b>ABU BOT</b>, {name}!\n🆔 Ваш ABU ID: <code>{abu_id}</code>",
        "welcome_back": "🌟 С возвращением, {name}!",
        "must_sub": "⚠️ Подпишитесь на каналы ниже и нажмите «Проверить».",
        "check_sub": "✅ Проверить", "still_missing": "❌ Вы подписались не на все каналы.",
        "lang_set": "✅ Язык изменён.", "settings": "⚙️ <b>Настройки</b>\n\n🌐 Выберите язык:",
        "no_tx": "Операций пока нет.",
    },
    "en": {
        "menu.cabinet": "👤 Cabinet", "menu.shop": "🛍 Shop", "menu.currencies": "💎 Currencies",
        "menu.gifts": "🎁 Gifts", "menu.nft": "🎨 NFT & Collectibles", "menu.tasks": "📋 Tasks",
        "menu.promo": "🎟 Promo code", "menu.referrals": "👥 Referrals", "menu.rating": "🏆 Ranking",
        "menu.settings": "⚙️ Settings", "menu.help": "❓ Help",
        "welcome": "🎉 Welcome to <b>ABU BOT</b>, {name}!\n🆔 Your ABU ID: <code>{abu_id}</code>",
        "welcome_back": "🌟 Welcome back, {name}!",
        "must_sub": "⚠️ Subscribe to the channels below, then press “Check”.",
        "check_sub": "✅ Check", "still_missing": "❌ You haven't joined all channels yet.",
        "lang_set": "✅ Language updated.", "settings": "⚙️ <b>Settings</b>\n\n🌐 Choose language:",
        "no_tx": "No transactions yet.",
    },
}


def t(lang: str, key: str, **kw) -> str:
    """Tarjima bo'lmasa, o'zbekchaga qaytadi."""
    s = T.get(lang, {}).get(key) or T["uz"].get(key) or key
    return s.format(**kw) if kw else s


def menu_labels(key: str) -> set[str]:
    return {T[l][f"menu.{key}"] for l in T if f"menu.{key}" in T[l]}

T["uz"].update({
    "shop_home": "🛍 <b>Do‘kon</b>\nBo‘limni tanlang:",
    "gifts_home": "🎁 <b>Sovg‘alar</b>\nBo‘limni tanlang:",
    "nft_home": "🎨 <b>NFT va Collectibles</b>\nBo‘limni tanlang:",
})
