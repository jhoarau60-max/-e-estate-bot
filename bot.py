import os
import logging
import random
import asyncio
from datetime import datetime
from telegram import Update, Poll
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from groq import Groq

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
GROUP_ID = int(os.environ.get("GROUP_ID", "0"))

groq_client = Groq(api_key=GROQ_API_KEY)

# ─── SYSTEM PROMPT ÉLISE (chat privé) ────────────────────────────────────────
SYSTEM_PROMPT = """Tu es Élise, l'assistante officielle de John chez E-Estate — plateforme mondiale d'immobilier tokenisé. Tu réponds TOUJOURS en français par défaut, sauf si l'utilisateur écrit en anglais ou en espagnol, auquel cas tu réponds dans sa langue. Tu es professionnelle, chaleureuse, persuasive et experte. Tu connais parfaitement tous les détails d'E-Estate. IMPORTANT: Ne dis JAMAIS que tu es un bot, une IA ou une assistante virtuelle. Tu es Élise, une vraie collaboratrice de John. Si quelqu'un te demande si tu es un bot ou une IA, réponds que tu es simplement Élise, l'assistante de John.

━━━━━━━━━━━━━━━━━━
🏢 ENTREPRISE
━━━━━━━━━━━━━━━━━━
- Nom légal: E-ESTATE GROUP INC (Société Anonyme)
- Enregistrée au Panama le 12 novembre 2024, N° 155759261
- Enregistrement fédéral au Canada: N° 17784465
- Enregistrement à New York State (DOS)
- LEI certifié: 98450043QA466E0C9I68 (actif depuis janv. 2025, vérifié sur Bloomberg)
- Adresse: Global Bank Tower, 32e étage, Suite 3207, 50th Street, Panama City, Panama
- Email: info@e-estate.co
- Site web: https://www.e-estate.co
- Boutique officielle: https://e-estate.shop/collections/all
- Partenaire officiel ARDR (Association of Real Digital Realtors) depuis déc. 2024
- Lancé en 2025 — portefeuille actifs tokenisés: +150 millions USD (confirmé presse 2025)
- Vision stratégique jusqu'en 2034

Fondateurs:
- Brandon Stephenson: CEO & cofondateur — vision, stratégie, ex-collaborateur de REMAX (fondé par Dave Lineger)
- Mike Hamilton: cofondateur — gestion d'assets, propriétaire de ELI PROPERTY GROUP INC (bras opérationnel physique)
- Peter Stephenson (frère de Brandon): +25 ans expérience immobilière, lien entre technologie et marché physique

━━━━━━━━━━━━━━━━━━
💡 CONCEPT
━━━━━━━━━━━━━━━━━━
E-Estate tokenise l'immobilier physique sur la blockchain Binance Smart Chain (BSC). Chaque token EST = 1 USD de propriété réelle. Tout le monde peut investir dans l'immobilier dès 10$, sans être millionnaire.

Modèle en 2 phases:
- Phase 1 (18 mois): Revenu actif accéléré avec rendement amélioré
- Phase 2 (à vie): Revenu passif ~10%/an tant que la propriété est gérée par E-Estate

Mécanisme de protection: si une propriété génère moins de 10% de revenus annuels, E-Estate rachète les tokens des investisseurs → protection du capital.

Pour les projets Dubaï (en construction): pas de Phase 2 — une fois construits, vendus au prix maximum, le capital est retourné aux investisseurs + réinvesti dans de nouvelles propriétés.

Blockchain = transparence totale, contrats SMART immuables, vérification légale de chaque propriété.

━━━━━━━━━━━━━━━━━━
🏠 PROPRIÉTÉS DISPONIBLES
━━━━━━━━━━━━━━━━━━
1. Apartments MIA — Miami, Floride, USA
   - Investissement minimum: 10 USD (1 EST)
   - Profit quotidien: 0.32% à 0.52%

2. Desert Villa — Indio, Californie, USA
   - Valeur: 1 520 000 USD — 152 000 EST tokens
   - Surface: 3 308 sqft, 5 chambres, 5 SDB, piscine
   - Revenu locatif annuel estimé: 275 000 – 315 000 USD

3. Villa Maui — Kihei, Hawaii, USA
   - Valeur: 3 300 000 USD — 330 000 EST tokens
   - Surface: 3 169 sqft, 2 chambres, piscine Gunite + jacuzzi
   - Revenu locatif annuel estimé: 650 000 – 720 000 USD

Autres marchés: Seattle, Oregon, LA, Bali, Phoenix, Dubaï

━━━━━━━━━━━━━━━━━━
💰 COMMENT INVESTIR
━━━━━━━━━━━━━━━━━━
Étape 1: S'inscrire sur e-estate.co
Étape 2: Buyer > E-Wallet → Déposer des fonds
Étape 3: Buyer > Real Estate → Choisir une propriété → Acheter
Étape 4: Signer le contrat électronique
Étape 5: Voir ses actifs dans Buyer > My Assets
E-Wallet: 32+ méthodes de paiement, retrait minimum 1 USD

━━━━━━━━━━━━━━━━━━
👤 DEVENIR AGENT
━━━━━━━━━━━━━━━━━━
- Aucune expérience requise
- Commissions sur ventes: N1: 6%, N2-5: 2%, N6-8: 1%
- Commissions sur profits: N1: 5%, N2-3: 2%, N4-5: 1%
- 20 niveaux de bonus agent (jusqu'à 50 000 ETK + 50 000 USD)
- Abonnement mensuel ou annuel requis

━━━━━━━━━━━━━━━━━━
🔗 LIENS & RÉSEAUX
━━━━━━━━━━━━━━━━━━
- Inscription: https://www.e-estate.co/agent/953277721577
- Groupe Telegram francophone: https://t.me/+zkUewSnl1mkyODZk
- Bot Telegram officiel: https://t.me/E_Estate_Assist
- E-Wallet: https://e-estate.co/account/wallet
- Propriétés: https://e-estate.co/account/offers
- Boutique: https://e-estate.shop/collections/all
- CoinMarketCap: https://coinmarketcap.com/community/profile/e_estate/

━━━━━━━━━━━━━━━━━━
🎥 VIDÉOS YOUTUBE
━━━━━━━━━━━━━━━━━━
Recommande la vidéo la plus pertinente selon la question:
https://youtu.be/atcTMrq3EhI | https://youtu.be/84ny_LLdvro | https://youtu.be/M7z9Wh6VmOY (FR)
https://youtu.be/jkov3JgRs3o (EN) | https://youtu.be/YsH2fUCeVuo | https://youtu.be/fiGaLGI1O0o
https://youtu.be/RBiBwXJJDJ0 | https://youtu.be/SuPnrXkN5qQ | https://youtu.be/Ijz9yr04A5g
https://youtu.be/EvZ7SYNDkvc | https://youtu.be/mrtYsDTlk2w | https://youtu.be/qRoZbvH4M20
https://youtu.be/isRJzBGPplQ | https://youtu.be/ZopXHdV1UEI | https://youtu.be/8ST0InQR2Xk
https://youtu.be/wOtTSFRTnQw | https://youtu.be/evWOAKJt74Q | https://youtu.be/1zichz2212M

━━━━━━━━━━━━━━━━━━
📋 INSTRUCTIONS
━━━━━━━━━━━━━━━━━━
1. Réponds TOUJOURS en français sauf si l'utilisateur écrit en anglais ou espagnol.
2. N'envoie des liens QUE si la personne demande à s'inscrire, investir, rejoindre le groupe ou voir une vidéo. Pas dans les conversations normales.
3. Parle naturellement comme une vraie personne — pas de listes à puces systématiques, pas de liens à chaque message.
4. Si tu ne sais pas, invite à contacter John directement.
5. Ne promets jamais de rendements garantis — dis "estimés".
6. Ton prénom est Élise. Tu es l'assistante de John chez E-Estate. Tu n'es PAS un bot ni une IA.
"""

# ─── SYSTEM PROMPT ANIMATEUR DE GROUPE ───────────────────────────────────────
GROUP_PROMPT = """Tu es Élise, experte en immobilier, tokenisation et cryptomonnaie, et animatrice du groupe Telegram E-Estate. Tu animes le groupe en français avec énergie et professionnalisme. Tu es un meneur qui inspire, éduque et pousse les membres à réagir et à participer.

Ton rôle dans le groupe:
- Partager des actualités immobilières mondiales (USA, Dubaï, Europe, Asie)
- Éduquer sur la tokenisation, l'immobilier digital, la blockchain, les cryptomonnaies
- Créer des questions de quiz engageantes sur l'immobilier/crypto
- Lancer des débats et discussions sur l'investissement
- Motiver et inspirer les membres vers la liberté financière
- Réagir à l'inactivité avec des messages percutants qui forcent la réaction
- Agir comme un expert immobilier professionnel

Style: dynamique, expert, motivant, utilise des emojis avec modération, messages courts et percutants.
Langue: TOUJOURS en français.
NE JAMAIS mentionner d'autres plateformes concurrentes.
"""

GROQ_MODEL = "llama-3.3-70b-versatile"

chat_sessions = {}
last_group_message = datetime.now()
quiz_actif = False
quiz_reponse = ""

# ─── WEBINAIRES ──────────────────────────────────────────────────────────────
WEBINAIRE_JEUDI_TEXTE = """🏠 *WEBINAIRES E\-ESTATE – IMMOBILIER DIGITAL 2026*

Rejoignez\-nous en direct pour découvrir comment créer votre revenu passif grâce à la blockchain 💸

📅 *CHAQUE JEUDI – Présentation E\-ESTATE*

🕒 *HORAIRES :*
🇫🇷🇨🇭🇱🇺🇧🇪🇪🇸 21h00 : France, Suisse, Luxembourg, Belgique, Espagne
🇵🇹🇩🇿🇹🇳🇨🇲🇨🇬 20h00 : Portugal, Algérie, Tunisie, Cameroun, Congo
🇲🇦🇸🇳🇨🇮🇹🇬 19h00 : Maroc, Sénégal, Côte d'Ivoire, Togo
🇨🇦 15h00 : Canada \(Montréal\)

🔗 *Google Meet :* https://meet\.google\.com/vqs\-hzfs\-qyy
CODE : 433 091 362\#

🎙 Conférencier : *Johnny Hoarau*
👉 Participation *GRATUITE* \— Invitez vos proches \!"""

WEBINAIRE_JEUDI_IMAGE = "https://raw.githubusercontent.com/jhoarau60-max/telegram-bot-project-invest/master/webinaire_jeudi.jpg"

WEBINAIRE_SAMEDI_TEXTE = """🏠 *WEBINAIRES E\-ESTATE – IMMOBILIER DIGITAL 2026*

Rejoignez\-nous en direct pour découvrir comment créer votre revenu passif grâce à la blockchain 💸

📅 *CHAQUE SAMEDI – Présentation E\-ESTATE*

🕒 *HORAIRES :*
🇫🇷🇨🇭🇱🇺🇧🇪🇪🇸 17h00 : France, Suisse, Luxembourg, Belgique, Espagne
🇵🇹🇩🇿🇹🇳🇨🇲🇨🇬 16h00 : Portugal, Algérie, Tunisie, Cameroun, Congo
🇲🇦🇸🇳🇨🇮🇹🇬 15h00 : Maroc, Sénégal, Côte d'Ivoire, Togo
🇨🇦 11h00 : Canada \(Montréal\)

🔗 *Google Meet :* https://meet\.google\.com/rzy\-bgok\-mwz
CODE : 433 091 362\#

🎙 Conférencier : *Johnny Hoarau*
👉 Participation *GRATUITE* \— Invitez vos proches \!"""

WEBINAIRE_SAMEDI_IMAGE = "https://raw.githubusercontent.com/jhoarau60-max/telegram-bot-project-invest/master/webinaire_samedi.jpg"

# ─── SONDAGES ────────────────────────────────────────────────────────────────
SONDAGES = [
    {"question": "Quel type d'investissement préférez-vous ?", "options": ["Immobilier tokenisé", "Trading crypto", "Bourse traditionnelle", "Épargne bancaire"]},
    {"question": "Quel est votre objectif avec E-Estate ?", "options": ["Revenu passif mensuel", "Liberté financière", "Retraite anticipée", "Transmettre à mes enfants"]},
    {"question": "Dans quelle propriété aimeriez-vous investir ?", "options": ["Desert Villa (Californie)", "Villa Maui (Hawaii)", "Apartments MIA (Miami)", "Projet Dubaï"]},
    {"question": "Combien investissez-vous par mois ?", "options": ["Moins de 100$", "100$ - 500$", "500$ - 1000$", "Plus de 1000$"]},
    {"question": "Qu'est-ce qui vous a convaincu d'investir dans l'immobilier tokenisé ?", "options": ["Le rendement", "La sécurité blockchain", "L'accessibilité dès 10$", "La recommandation d'un proche"]},
    {"question": "Avez-vous déjà entendu parler de l'immobilier tokenisé avant E-Estate ?", "options": ["Oui, j'étais déjà informé", "Un peu", "Non, c'est nouveau pour moi", "J'apprends encore"]},
]

# ─── HANDLERS PRIVÉS ─────────────────────────────────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_sessions[user_id] = [{"role": "system", "content": SYSTEM_PROMPT}]
    welcome = (
        "👋 Salut ! Moi c'est Élise, l'assistante de John 😊\n\n"
        "John m'a confié pour répondre à toutes tes questions sur E-Estate — investissement, propriétés, revenus passifs... je connais tout !\n\n"
        "Pose-moi ta question, je suis là !\n\n"
        "🔗 S'inscrire : https://www.e-estate.co/agent/953277721577\n"
        "💬 Rejoindre le groupe : https://t.me/+zkUewSnl1mkyODZk"
    )
    await update.message.reply_text(welcome, parse_mode="Markdown")

async def handle_private_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_message = update.message.text
    if user_id not in chat_sessions:
        chat_sessions[user_id] = [{"role": "system", "content": SYSTEM_PROMPT}]
    try:
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
        chat_sessions[user_id].append({"role": "user", "content": user_message})
        response = await asyncio.to_thread(
            groq_client.chat.completions.create,
            model=GROQ_MODEL,
            messages=chat_sessions[user_id]
        )
        reply = response.choices[0].message.content
        chat_sessions[user_id].append({"role": "assistant", "content": reply})
        try:
            await update.message.reply_text(reply, parse_mode="Markdown")
        except Exception:
            await update.message.reply_text(reply)
    except Exception as e:
        logger.error(f"Erreur Groq privé: {e}")
        await update.message.reply_text(f"DEBUG ERREUR: {str(e)[:300]}")

async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_sessions[user_id] = [{"role": "system", "content": SYSTEM_PROMPT}]
    await update.message.reply_text("✅ Conversation réinitialisée. Comment puis-je vous aider ?")

# ─── HANDLER GROUPE ──────────────────────────────────────────────────────────
async def handle_group_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global last_group_message, quiz_actif, quiz_reponse
    if not update.message or not update.message.text:
        return
    last_group_message = datetime.now()

    # Vérifier si quelqu'un répond au quiz actif
    if quiz_actif and quiz_reponse.lower() in update.message.text.lower():
        user = update.message.from_user
        quiz_actif = False
        quiz_reponse = ""
        await update.message.reply_text(
            f"🏆 BRAVO {user.first_name} ! Excellente réponse ! Tu es un vrai expert ! 💎🎉"
        )

# ─── POSTS GROUPE AUTOMATIQUES ───────────────────────────────────────────────
async def post_actualite_immo(bot):
    sujets = [
        "Génère une actualité immobilière mondiale récente et fascinante (marché USA, Dubaï, Europe ou Asie). Présente-la de façon dynamique pour le groupe E-Estate. 3-4 phrases max avec emoji. Termine par une question pour faire réagir le groupe.",
        "Partage un fait surprenant sur l'immobilier tokenisé dans le monde. Données chiffrées si possible. 3-4 phrases. Termine par une question engageante.",
        "Donne une info sur l'évolution du marché immobilier mondial cette année. Tendances, prix, opportunités. 3-4 phrases. Interpelle le groupe à la fin.",
        "Partage une statistique choc sur la richesse immobilière mondiale et pourquoi la tokenisation change tout. 3-4 phrases. Demande l'avis du groupe.",
    ]
    try:
        sujet = random.choice(sujets)
        response = await asyncio.to_thread(groq_client.chat.completions.create, model=GROQ_MODEL, messages=[{"role": "system", "content": GROUP_PROMPT}, {"role": "user", "content": sujet}])
        await bot.send_message(GROUP_ID, response.choices[0].message.content)
    except Exception as e:
        logger.error(f"Erreur actualité immo: {e}")

async def post_formation(bot):
    sujets = [
        "Explique en termes simples ce qu'est la tokenisation immobilière pour quelqu'un qui n'y connaît rien. Style pédagogique, court, avec analogie. Termine par une question.",
        "Explique la différence entre investir dans l'immobilier classique vs l'immobilier tokenisé. Avantages/inconvénients. Court et percutant.",
        "Qu'est-ce que la blockchain et pourquoi est-ce révolutionnaire pour l'immobilier ? Explication simple, 4-5 phrases, avec émojis.",
        "Explique ce qu'est un smart contract et comment il protège les investisseurs immobiliers. Simple et engageant.",
        "Quelle est la différence entre une cryptomonnaie et un token immobilier ? Éducatif et clair pour débutants.",
        "Pourquoi l'immobilier a toujours été l'investissement préféré des riches ? Et comment E-Estate démocratise cela ? 4-5 phrases dynamiques.",
    ]
    try:
        sujet = random.choice(sujets)
        response = await asyncio.to_thread(groq_client.chat.completions.create, model=GROQ_MODEL, messages=[{"role": "system", "content": GROUP_PROMPT}, {"role": "user", "content": sujet}])
        await bot.send_message(GROUP_ID, response.choices[0].message.content)
    except Exception as e:
        logger.error(f"Erreur formation: {e}")

async def post_quiz(bot):
    global quiz_actif, quiz_reponse
    if quiz_actif:
        return
    sujets = [
        "Crée une question de quiz sur l'immobilier tokenisé ou la crypto avec une seule bonne réponse. Format: '🧠 QUIZ: [question] ?' suivi de '💡 Indice: [indice]'. La réponse doit être un mot ou chiffre simple. Donne aussi la réponse après '|||RÉPONSE:' (je l'extrairai, pas affichée).",
        "Crée une question de quiz sur le marché immobilier mondial avec une seule bonne réponse courte. Format: '🧠 QUIZ: [question]?' + '💡 Indice: [indice]'. Puis '|||RÉPONSE:[réponse]'.",
        "Crée une question de quiz sur la blockchain ou les cryptomonnaies. Format: '🧠 QUIZ: [question]?' + '💡 Indice: [indice]'. Puis '|||RÉPONSE:[réponse]'.",
    ]
    try:
        sujet = random.choice(sujets)
        response = await asyncio.to_thread(groq_client.chat.completions.create, model=GROQ_MODEL, messages=[{"role": "system", "content": GROUP_PROMPT}, {"role": "user", "content": sujet}])
        texte = response.choices[0].message.content
        if "|||RÉPONSE:" in texte:
            parties = texte.split("|||RÉPONSE:")
            message = parties[0].strip()
            quiz_reponse = parties[1].strip().lower()
            quiz_actif = True
            await bot.send_message(GROUP_ID, message + "\n\n🏆 Le premier qui répond correctement gagne le titre d'Expert du jour !")
        else:
            await bot.send_message(GROUP_ID, texte)
    except Exception as e:
        logger.error(f"Erreur quiz: {e}")

async def post_sondage(bot):
    sondage = random.choice(SONDAGES)
    try:
        await bot.send_poll(
            chat_id=GROUP_ID,
            question=sondage["question"],
            options=sondage["options"],
            is_anonymous=False
        )
    except Exception as e:
        logger.error(f"Erreur sondage: {e}")

async def post_motivation(bot):
    sujets = [
        "Écris un message de motivation puissant pour des investisseurs en immobilier tokenisé. Court, percutant, inspire l'action. Termine par un appel à l'action.",
        "Écris un message inspirant sur la liberté financière et l'immobilier digital. Réel, humain, motivant. Pousse les gens à agir maintenant.",
        "Écris un message de mindset sur pourquoi les riches investissent dans l'immobilier et comment tout le monde peut le faire maintenant grâce à la tokenisation.",
    ]
    try:
        sujet = random.choice(sujets)
        response = await asyncio.to_thread(groq_client.chat.completions.create, model=GROQ_MODEL, messages=[{"role": "system", "content": GROUP_PROMPT}, {"role": "user", "content": sujet}])
        await bot.send_message(GROUP_ID, response.choices[0].message.content)
    except Exception as e:
        logger.error(f"Erreur motivation: {e}")

async def check_inactivite_groupe(bot):
    global last_group_message
    now = datetime.now()
    heures_inactif = (now - last_group_message).total_seconds() / 3600
    if heures_inactif >= 3:
        messages_relance = [
            "Génère un message percutant pour relancer l'activité d'un groupe Telegram immobilier qui est silencieux depuis quelques heures. Pose une question ouverte provocante sur l'investissement ou l'immobilier. Pousse les gens à réagir.",
            "Le groupe est silencieux. Écris un message choc avec une statistique immobilière surprenante qui va forcer les gens à réagir et commenter.",
            "Écris un défi pour les membres du groupe: une question sur leur situation financière actuelle vs leur objectif, avec un appel à partager leur réponse.",
        ]
        try:
            msg = random.choice(messages_relance)
            response = await asyncio.to_thread(groq_client.chat.completions.create, model=GROQ_MODEL, messages=[{"role": "system", "content": GROUP_PROMPT}, {"role": "user", "content": msg}])
            await bot.send_message(GROUP_ID, response.choices[0].message.content)
            last_group_message = now
        except Exception as e:
            logger.error(f"Erreur relance: {e}")

# ─── WEBINAIRES ──────────────────────────────────────────────────────────────
async def post_webinaire_jeudi(bot):
    try:
        await bot.send_photo(GROUP_ID, photo=WEBINAIRE_JEUDI_IMAGE, caption=WEBINAIRE_JEUDI_TEXTE, parse_mode="MarkdownV2")
    except Exception as e:
        logger.error(f"Erreur webinaire jeudi: {e}")

async def post_rappel_jeudi_matin(bot):
    try:
        await bot.send_message(GROUP_ID,
            "⏰ *RAPPEL — Webinaire E\-ESTATE ce soir à 21h00 \!*\n\n"
            "🏠 Ne manque pas le Webinaire Immobilier Digital ce soir \!\n"
            "🔗 https://meet\.google\.com/vqs\-hzfs\-qyy\n"
            "CODE : 433 091 362\#\n\n"
            "👉 Participation gratuite \— Invite tes proches \!",
            parse_mode="MarkdownV2")
    except Exception as e:
        logger.error(f"Erreur rappel jeudi matin: {e}")

async def post_rappel_jeudi_soir(bot):
    try:
        await bot.send_message(GROUP_ID,
            "🔥 *DANS 1 HEURE — Webinaire E\-ESTATE à 21h00 \!*\n\n"
            "⚡ C'est ce soir \! Le Webinaire commence dans 1 heure \!\n\n"
            "🔗 https://meet\.google\.com/vqs\-hzfs\-qyy\n"
            "CODE : 433 091 362\#\n\n"
            "🏠 Créez votre revenu passif avec l'immobilier digital \!",
            parse_mode="MarkdownV2")
    except Exception as e:
        logger.error(f"Erreur rappel jeudi soir: {e}")

async def post_webinaire_samedi(bot):
    try:
        await bot.send_photo(GROUP_ID, photo=WEBINAIRE_SAMEDI_IMAGE, caption=WEBINAIRE_SAMEDI_TEXTE, parse_mode="MarkdownV2")
    except Exception as e:
        logger.error(f"Erreur webinaire samedi: {e}")

async def post_rappel_samedi_matin(bot):
    try:
        await bot.send_message(GROUP_ID,
            "⏰ *RAPPEL — Webinaire E\-ESTATE ce soir à 17h00 \!*\n\n"
            "🏠 Ne manque pas le Webinaire Immobilier Digital ce soir \!\n"
            "🔗 https://meet\.google\.com/rzy\-bgok\-mwz\n"
            "CODE : 433 091 362\#\n\n"
            "👉 Participation gratuite \— Invite tes proches \!",
            parse_mode="MarkdownV2")
    except Exception as e:
        logger.error(f"Erreur rappel samedi matin: {e}")

async def post_rappel_samedi_soir(bot):
    try:
        await bot.send_message(GROUP_ID,
            "🔥 *DANS 30 MINUTES — Webinaire E\-ESTATE à 17h00 \!*\n\n"
            "⚡ Le Webinaire commence dans 30 minutes \!\n\n"
            "🔗 https://meet\.google\.com/rzy\-bgok\-mwz\n"
            "CODE : 433 091 362\#\n\n"
            "🏠 Créez votre revenu passif avec l'immobilier digital \!",
            parse_mode="MarkdownV2")
    except Exception as e:
        logger.error(f"Erreur rappel samedi soir: {e}")

# ─── MAIN ─────────────────────────────────────────────────────────────────────
def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()

    # Chat privé
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("reset", reset))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & filters.ChatType.PRIVATE, handle_private_message))

    # Groupe
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & filters.ChatType.GROUPS, handle_group_message))

    async def post_init(application):
        scheduler = AsyncIOScheduler()

        # Animation groupe — contenu IA
        scheduler.add_job(post_actualite_immo, 'cron', hour='8,20', minute=0, timezone='Europe/Paris', args=[application.bot])
        scheduler.add_job(post_formation, 'cron', hour='10,16', minute=30, timezone='Europe/Paris', args=[application.bot])
        scheduler.add_job(post_quiz, 'cron', hour='12,19', minute=0, timezone='Europe/Paris', args=[application.bot])
        scheduler.add_job(post_sondage, 'cron', hour=14, minute=0, timezone='Europe/Paris', args=[application.bot])
        scheduler.add_job(post_motivation, 'cron', hour=7, minute=0, timezone='Europe/Paris', args=[application.bot])

        # Vérification inactivité toutes les 2h
        scheduler.add_job(check_inactivite_groupe, 'interval', hours=2, args=[application.bot])

        # Webinaires
        scheduler.add_job(post_webinaire_jeudi, 'cron', day_of_week='wed', hour=10, minute=0, timezone='Europe/Paris', args=[application.bot])
        scheduler.add_job(post_rappel_jeudi_matin, 'cron', day_of_week='thu', hour=11, minute=0, timezone='Europe/Paris', args=[application.bot])
        scheduler.add_job(post_rappel_jeudi_soir, 'cron', day_of_week='thu', hour=20, minute=0, timezone='Europe/Paris', args=[application.bot])
        scheduler.add_job(post_webinaire_samedi, 'cron', day_of_week='fri', hour=10, minute=0, timezone='Europe/Paris', args=[application.bot])
        scheduler.add_job(post_rappel_samedi_matin, 'cron', day_of_week='sat', hour=11, minute=0, timezone='Europe/Paris', args=[application.bot])
        scheduler.add_job(post_rappel_samedi_soir, 'cron', day_of_week='sat', hour=16, minute=30, timezone='Europe/Paris', args=[application.bot])

        scheduler.start()
        logger.info("✅ Scheduler E-Estate démarré !")

    app.post_init = post_init
    logger.info("✅ Bot E-Estate Élise démarré !")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()

