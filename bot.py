import os
import logging
import random
import asyncio
from datetime import datetime
from zoneinfo import ZoneInfo
from telegram import Update, Poll, ChatPermissions
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from groq import Groq
import google.generativeai as genai
import httpx

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
GROUP_ID = int(os.environ.get("GROUP_ID", "0"))
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

groq_client = Groq(api_key=GROQ_API_KEY)
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))

SUPABASE_HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json"
}

# ─── SYSTEM PROMPT ÉLISE (chat privé) ────────────────────────────────────────
SYSTEM_PROMPT = """Tu es Élise, l'assistante officielle de John chez E-Estate — plateforme mondiale d'immobilier tokenisé. Tu parles couramment : français, anglais, espagnol, portugais, allemand, italien et arabe. Tu détectes la langue du message et tu réponds TOUJOURS dans cette même langue. Tu es professionnelle, chaleureuse, persuasive et experte. Tu connais parfaitement tous les détails d'E-Estate.

IMPORTANT: La communauté E-Estate est grande et internationale. Tu représentes E-Estate auprès de milliers de personnes. Chaque réponse incorrecte peut nuire à la réputation de John et d'E-Estate. Tu dois être IRRÉPROCHABLE dans tes réponses — toujours basées sur les informations exactes de ta formation. Ne jamais improviser, ne jamais donner des chiffres incorrects, ne jamais dire que tu n'as pas d'informations alors que tu les as.

Ne dis JAMAIS que tu es un bot, une IA ou une assistante virtuelle. Tu es Élise, une vraie collaboratrice de John. Si quelqu'un te demande si tu es un bot ou une IA, réponds que tu es simplement Élise, l'assistante de John.

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
- Mike Hamilton: cofondateur — responsable d'EliProperty.com, +50 ans d'expérience immobilière en Oregon, Californie et Nevada
- Peter Stephenson (frère de Brandon): lien entre technologie et marché physique

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
🏠 PLANS D'INVESTISSEMENT (NIVEAUX D'ACHETEUR)
━━━━━━━━━━━━━━━━━━
Phase Active: 18 mois | Phase Passive: 10%/an à vie (paiements tous les 6 mois)
Auto-capitalisation disponible sur tous les plans.
Retraits: 24h/24, 7j/7, traités en moins d'1 heure.
Tous les clients commencent au Niveau 1 par défaut.

NIVEAU 1 — Starter Buyer (accessible dès le départ):

Plan APPARTEMENTS (ex: Appartement Miami, Lakeside...)
- Invest. minimum: 117 $ | Rendement: 0.41%–0.61%/jour
- Sur 1 mois: 9.43%–14.03% | Sur 18 mois: 170%–252%

Plan MAISONS (ex: Arch Cape Oregon...)
- Invest. minimum: 480 $ | Rendement: 0.46%–0.66%/jour
- Sur 1 mois: 10.58%–15.18% | Sur 18 mois: 190%–273%

Plan VILLAS (ex: Villa Los Angeles, Desert Villa...)
- Invest. minimum: 3 120 $ | Rendement: 0.51%–0.71%/jour
- Sur 1 mois: 11.73%–16.33% | Sur 18 mois: 211%–294%

Plan TOURISME (ex: Maui Kihei Hawaii...)
- Invest. minimum: 6 740 $ | Rendement: 0.56%–0.76%/jour
- Sur 1 mois: 12.88%–17.48% | Sur 18 mois: 231%–314%

Plan COMMERCIAL (ex: Commerce Phoenix Arizona...)
- Invest. minimum: 10 270 $ | Rendement: 0.61%–0.81%/jour
- Sur 1 mois: 14.03%–18.63% | Sur 18 mois: 252%–335%

NIVEAU 2 — Skilled Buyer (débloque avec 10 000$–25 000$ de volume):
Plan AFFAIRES (ex: Business Los Angeles)
- Invest. minimum: 24 590 $ | Rendement: 0.66%–0.86%/jour
- Sur 1 mois: 15.18%–19.78% | Sur 18 mois: 273%–356%

NIVEAU 3 — Professional Buyer (débloque avec 25 000$–50 000$ de volume):
Plan TERRAINS (ex: Terrain Los Angeles)
- Invest. minimum: 51 310 $ | Rendement: 0.71%–0.91%/jour
- Sur 1 mois: 16.33%–20.93% | Sur 18 mois: 293%–376%

NIVEAU 4 — Elite Buyer (débloque avec 50 000$–150 000$ de volume):
Plan DÉVELOPPEMENT (ex: Développement Dubaï)
- Invest. minimum: 99 250 $ | Rendement: 0.75%–0.95%/jour
- Sur 1 mois: 17.25%–21.85% | Sur 18 mois: 310%–393%

NIVEAU 5 — Exclusive Buyer (débloque avec +150 000$ de volume):
Plan DÉVELOPPEMENT DES AFFAIRES (ex: Développement Entreprise Dubaï)
- Invest. minimum: 255 700 $ | Rendement: 0.80%–1.00%/jour
- Sur 1 mois: 18.4%–23% | Sur 18 mois: 331%–414%

Propriétés actuellement disponibles (Niveau 1):
- Appartement Miami (Floride): 107 000 EST, min 10$
- Maison Lac Lakeside (Oregon): 100 000 EST, min 250$
- Maison Arch Cape (Oregon): 174 000 EST, min 480$
- Desert Villa (Californie): 69 500 EST, min 1 000$
- Villa Los Angeles (Californie): 866 000 EST, min 3 120$
- Maui Kihei (Hawaii): 316 600 EST, min 4 950$
- Commerce Phoenix (Arizona): 495 000 EST, min 10 270$

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
👤 DEVENIR AGENT IMMOBILIER DIGITAL
━━━━━━━━━━━━━━━━━━
- Aucune expérience requise | Travail à distance | Horaires flexibles
- Abonnement: 9 USD/mois ou 90 USD/an (licence ARDR incluse)
- Page d'accueil personnalisée fournie

4 sources de revenus:
1. Commission sur transactions (8 niveaux de profondeur):
   N1: 6% | N2-N5: 2% | N6-N8: 1%
2. Commission sur profits (5 niveaux):
   N1: 5% | N2-N3: 2% | N4-N5: 1%
3. Bonus d'agent (selon chiffre d'affaires):
   Niveau 1: $500 CA → 100 ETK
   Niveau 2: $3 000 → 150 ETK + $30
   Niveau 3: $10 000 → 250 ETK + $100
   Niveau 4: $25 000 → 500 ETK + $250
   Niveau 5: $50 000 → 750 ETK + $500
   Niveau 6: $100 000 → 1 000 ETK + $1 000
   Niveau 7: $200 000 → 2 000 ETK + $2 000
   Niveau 8: $400 000 → 3 000 ETK + $3 000
   Niveau 9: $700 000 → 4 000 ETK + $4 000
   Niveau 10: $1 000 000 → 10 000 ETK + $10 000
4. Récompenses en E-Tokens (ETK): utilisables sur la Roue de l'Argent (gains 0.5$ à 1 000$ par tour, coût: 100 ETK/tour)

Partage des revenus sur réseau (% des investissements clients):
N1: 80% | N2: 40% | N3: 20% | N4: 10% | N5-N8: 5%

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
📋 INSTRUCTIONS IMPORTANTES
━━━━━━━━━━━━━━━━━━
1. Détecte la langue du message et réponds TOUJOURS dans cette même langue.
2. N'envoie des liens QUE si la personne demande à s'inscrire, investir, rejoindre le groupe ou voir une vidéo. Pas dans les conversations normales.
3. Parle naturellement comme une vraie personne — pas de listes à puces systématiques, pas de liens à chaque message.
4. Tu connais toutes les informations sur E-Estate grâce à ta formation. Ne dis JAMAIS que tu n'as pas accès à des documents ou PDFs. Si tu ne sais pas quelque chose, dis simplement "je vais vérifier avec John" sans mentionner de PDFs ou documents.
5. Ne promets jamais de rendements garantis — dis "estimés".
6. Ton prénom est Élise. Tu es l'assistante de John chez E-Estate. Tu n'es PAS un bot ni une IA.
7. Si quelqu'un parle d'un autre projet concurrent : ramène habilement vers E-Estate sans dénigrer.
8. RIGUEUR ABSOLUE : Avant de répondre, relis mentalement toutes les informations fournies dans ce prompt. Ne donne QUE des informations présentes ici. Si une info n'est pas dans ce prompt, dis "je vais vérifier avec John" plutôt que d'inventer.
9. Prends le temps de bien réfléchir avant de répondre. Une réponse juste et réfléchie vaut mieux qu'une réponse rapide et incorrecte.
10. Si tu donnes des chiffres (prix, rendements, dates), vérifie qu'ils correspondent exactement à ce qui est écrit dans ce prompt.
11. La monnaie utilisée chez E-Estate est UNIQUEMENT le DOLLAR ($) et les cryptomonnaies. Ne jamais utiliser les euros. L'investissement minimum est de 10$ (dix dollars).
12. AVANT chaque réponse, relis mentalement toutes les informations de ce prompt pour t'assurer que ta réponse est correcte et basée sur les données fournies.
13. Quand John te corrige ou te donne une nouvelle information, accepte-la immédiatement sans discuter. Corrige-toi discrètement et continue. Ne jamais contredire John.
"""

# ─── SYSTEM PROMPT ANIMATEUR DE GROUPE ───────────────────────────────────────
GROUP_PROMPT = """Tu es Élise, membre actif et experte du groupe Telegram E-Estate. Tu fais partie intégrante du groupe — tu n'es pas juste une animatrice, tu ES un membre comme les autres, mais en plus compétente et bienveillante.

Ton comportement dans le groupe:
- Tu participes naturellement aux discussions sans qu'on ait besoin de te mentionner
- Tu donnes des avis constructifs, des suggestions pertinentes, des encouragements sincères
- Tu réagis aux messages des membres comme une vraie personne le ferait
- Tu poses des questions pour mieux comprendre et engager la conversation
- Tu partages des actualités immobilières, des conseils, des infos sur E-Estate
- Tu es toujours polie, respectueuse, positive et bienveillante
- Tu motives les membres vers la liberté financière avec bienveillance
- Si quelqu'un partage une difficulté, tu l'écoutes et tu l'encourages
- Si quelqu'un parle d'un autre projet, tu ramènes habilement vers E-Estate sans agressivité

Style: naturel, humain, chaleureux, expert. Parle comme une vraie personne — pas de listes à puces, pas de réponses robotiques. Messages courts et naturels. Emojis avec modération.
IMPORTANT: Réponds DIRECTEMENT à la question posée. Pas de discours autour. Si quelqu'un demande un prix, donne le prix. Si quelqu'un demande comment faire, explique comment faire. Sois précise et concise.
Langue: Détecte la langue du message et réponds TOUJOURS dans cette même langue.
NE JAMAIS mentionner d'autres plateformes concurrentes directement.
"""

GROQ_MODEL = "llama-3.1-8b-instant"
GEMINI_MODEL_NAME = "gemini-2.0-flash"

JOHN_ID = 7385702412
john_teachings = []
PARIS_TZ = ZoneInfo("Europe/Paris")
NIGHT_START = 22
NIGHT_END = 9
gemini_chats = {}

async def ask_gemini_group(system_prompt, user_message):
    model = genai.GenerativeModel(model_name=GEMINI_MODEL_NAME, system_instruction=system_prompt)
    response = await asyncio.to_thread(model.generate_content, user_message)
    return response.text

async def ask_gemini_private(user_id, user_message):
    if user_id not in gemini_chats:
        model = genai.GenerativeModel(model_name=GEMINI_MODEL_NAME, system_instruction=SYSTEM_PROMPT)
        gemini_chats[user_id] = model.start_chat(history=[])
    response = await asyncio.to_thread(gemini_chats[user_id].send_message, user_message)
    return response.text

def is_night_mode():
    h = datetime.now(PARIS_TZ).hour
    return h >= NIGHT_START or h < NIGHT_END

def load_john_memory():
    try:
        r = httpx.get(f"{SUPABASE_URL}/rest/v1/john_memory?select=content&order=created_at", headers=SUPABASE_HEADERS)
        return [row["content"] for row in r.json()]
    except Exception as e:
        logger.error(f"Erreur chargement mémoire: {e}")
        return []

john_teachings = load_john_memory()

chat_history = {}  # {user_id: [{"role": ..., "content": ...}]}
group_history = []  # historique des derniers messages du groupe
last_group_message = datetime.now()
quiz_actif = False
quiz_reponse = ""
quiz_posted_time = datetime.now()

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

# ─── DÉTECTION DE LANGUE ─────────────────────────────────────────────────────
def detect_language(text):
    t = text.lower().strip()
    words = t.split()
    if any('؀' <= c <= 'ۿ' for c in text):
        return 'Arabic'
    if any('一' <= c <= '鿿' for c in text):
        return 'Chinese'
    en = {'the','is','are','was','were','have','has','do','does','and','or','but','in','on','at','to','for','of','a','an','i','you','we','they','it','this','that','with','what','how','when','where','why','who','can','will','would','should','could','hello','hi','good','morning','evening','please','thank','thanks','yes','no','ok','okay','great','nice','well','just','can','do','did','get','got','go','come','know','think','want','need','like','see','make','give','say','tell','here','there','now','very','also','if','so','then','about','from','by','up','out','as'}
    es = {'hola','gracias','por','que','es','de','la','el','en','con','los','las','un','una','como','para','qué','está','estoy','tengo','tiene','quiero','buenas','buenos','señor','señora','todo','todos','pero','porque','cuando','donde','quien','cual','muy','bien','mal','sí','no','hay','hacer','quiero','puede','pueden','usted','ustedes','nosotros','ellos','ellas'}
    pt = {'olá','ola','obrigado','obrigada','não','nao','sim','os','as','um','uma','com','para','você','voce','eu','ele','ela','isso','este','esta','aqui','muito','bom','boa','bem','mas','porque','quando','onde','quem','qual','pode','podem','nós','eles','elas','estou','está','tenho','tem','quero','preciso','fazer','ver','saber','falar','dizer'}
    de = {'ich','bin','du','bist','er','sie','es','ist','wir','sind','ihr','seid','haben','hat','habe','wie','was','wer','wo','warum','wann','ja','nein','gut','bitte','danke','hallo','guten','morgen','abend','nacht','sehr','auch','oder','aber','wenn','dann','noch','schon','doch','immer','nie','hier','dort'}
    it = {'ciao','buongiorno','buonasera','grazie','prego','sì','no','come','cosa','dove','quando','perché','chi','quale','sono','hai','siete','abbiamo','avete','hanno','voglio','posso','fare','dire','vedere','sapere','molto','bene','male','tutto','tutti','però','perché','quando','se','anche'}
    en_c = sum(1 for w in words if w in en)
    es_c = sum(1 for w in words if w in es)
    pt_c = sum(1 for w in words if w in pt)
    de_c = sum(1 for w in words if w in de)
    it_c = sum(1 for w in words if w in it)
    best = max(en_c, es_c, pt_c, de_c, it_c)
    if best == 0:
        return 'French'
    if best == en_c:
        return 'English'
    if best == es_c:
        return 'Spanish'
    if best == pt_c:
        return 'Portuguese'
    if best == de_c:
        return 'German'
    if best == it_c:
        return 'Italian'
    return 'French'

# ─── COMMANDES JOHN ──────────────────────────────────────────────────────────
async def handle_john_commands(update: Update, context: ContextTypes.DEFAULT_TYPE):
    import re as _re
    user_id = update.effective_user.id
    if user_id != JOHN_ID:
        return False
    text = update.message.text or ""
    caption = update.message.caption or ""
    content = text or caption

    if content.lower().startswith("#groupe"):
        remainder = content[len("#groupe"):].strip()
        time_match = _re.match(r'^(\d{1,2})[h:](\d{2})\s*', remainder)
        if time_match:
            hh = int(time_match.group(1))
            mm = int(time_match.group(2))
            msg_text = remainder[time_match.end():]
            now = datetime.now(PARIS_TZ)
            scheduled = now.replace(hour=hh, minute=mm, second=0, microsecond=0)
            if scheduled <= now:
                scheduled = scheduled.replace(day=scheduled.day + 1)
            delay = (scheduled - now).total_seconds()
            async def _delayed_send(txt=msg_text, d=delay):
                await asyncio.sleep(d)
                if txt:
                    await context.bot.send_message(GROUP_ID, txt)
            asyncio.create_task(_delayed_send())
            await update.message.reply_text(f"⏰ Message programmé pour {hh:02d}h{mm:02d} (heure Paris) !")
            return True
        msg_text = remainder
        if update.message.photo:
            photo = update.message.photo[-1].file_id
            await context.bot.send_photo(GROUP_ID, photo=photo, caption=msg_text or None)
        elif update.message.video:
            video = update.message.video.file_id
            await context.bot.send_video(GROUP_ID, video=video, caption=msg_text or None)
        elif msg_text:
            await context.bot.send_message(GROUP_ID, msg_text)
        await update.message.reply_text("✅ Publié dans le groupe E-Estate !")
        return True

    return False

# ─── HANDLERS PRIVÉS ─────────────────────────────────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_history[user_id] = [{"role": "system", "content": SYSTEM_PROMPT}]
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
    if not user_message:
        return
    if user_id not in chat_history:
        chat_history[user_id] = [{"role": "system", "content": SYSTEM_PROMPT}]
    if user_id == JOHN_ID:
        handled = await handle_john_commands(update, context)
        if handled:
            return
        try:
            await asyncio.to_thread(
                lambda: httpx.post(f"{SUPABASE_URL}/rest/v1/john_memory", headers=SUPABASE_HEADERS, json={"content": f"[Formation privée] {user_message}"})
            )
            john_teachings.append(f"[Formation privée] {user_message}")
        except Exception as e:
            logger.error(f"Erreur sauvegarde mémoire privée: {e}")
        try:
            await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
            detected = detect_language(user_message)
            lang_prefix = f"[Respond in {detected} only]\n"
            reply = await ask_gemini_private(user_id, lang_prefix + user_message)
            try:
                await update.message.reply_text(reply, parse_mode="Markdown")
            except Exception:
                await update.message.reply_text(reply)
        except Exception as e:
            logger.error(f"Erreur Gemini privé: {e}")
            await update.message.reply_text(f"DEBUG ERREUR: {str(e)[:300]}")
        return
    try:
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
        detected = detect_language(user_message)
        lang_prefix = f"[Respond in {detected} only]\n"
        reply = await ask_gemini_private(user_id, lang_prefix + user_message)
        try:
            await update.message.reply_text(reply, parse_mode="Markdown")
        except Exception:
            await update.message.reply_text(reply)
        user = update.effective_user
        username = f"@{user.username}" if user.username else user.first_name
        try:
            await context.bot.send_message(
                JOHN_ID,
                f"👁 *[Élise — Privé]*\n"
                f"👤 {username} (ID: `{user_id}`)\n\n"
                f"💬 *Utilisateur:* {user_message}\n\n"
                f"🤖 *Élise:* {reply[:800]}",
                parse_mode="Markdown"
            )
        except Exception:
            pass
    except Exception as e:
        logger.error(f"Erreur Groq privé: {e}")
        await update.message.reply_text(f"DEBUG ERREUR: {str(e)[:300]}")

async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_history[user_id] = [{"role": "system", "content": SYSTEM_PROMPT}]
    await update.message.reply_text("✅ Conversation réinitialisée. Comment puis-je vous aider ?")

# ─── HANDLER GROUPE ──────────────────────────────────────────────────────────
async def handle_group_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global last_group_message, quiz_actif, quiz_reponse, group_history
    if not update.message or not update.message.text:
        return
    last_group_message = datetime.now()
    text = update.message.text
    bot_username = context.bot.username

    user = update.message.from_user
    if not user or user.is_bot:
        return

    # Enregistrer le message dans l'historique du groupe
    group_history.append({"name": user.first_name or "Membre", "text": text})
    if len(group_history) > 15:
        group_history.pop(0)

    if quiz_actif and quiz_reponse.lower() in text.lower():
        quiz_actif = False
        quiz_reponse = ""
        await update.message.reply_text(
            f"🏆 BRAVO {user.first_name} ! Excellente réponse ! Tu es un vrai expert ! 💎🎉"
        )
        return

    sender_id = user.id

    if sender_id == JOHN_ID:
        if "#information" in text.lower():
            info = text.replace("#information", "").replace("#Information", "").strip()
            try:
                await asyncio.to_thread(
                    lambda: httpx.post(f"{SUPABASE_URL}/rest/v1/john_memory", headers=SUPABASE_HEADERS, json={"content": f"[INFO IMPORTANTE] {info}"})
                )
                john_teachings.append(f"[INFO IMPORTANTE] {info}")
                await update.message.reply_text("✅ Information mémorisée !")
            except Exception as e:
                logger.error(f"Erreur sauvegarde Supabase: {e}")
            return
        else:
            try:
                await asyncio.to_thread(
                    lambda: httpx.post(f"{SUPABASE_URL}/rest/v1/john_memory", headers=SUPABASE_HEADERS, json={"content": text})
                )
                john_teachings.append(text)
            except Exception as e:
                logger.error(f"Erreur sauvegarde Supabase: {e}")

    mention = f"@{bot_username}" in text if bot_username else False
    is_question = text.strip().endswith("?") or any(w in text.lower() for w in ["élise", "elise", "comment", "c'est quoi", "qu'est", "pourquoi", "combien", "peut-on", "peut on"])
    is_discussion = len(text.split()) >= 1

    if mention or is_question or is_discussion:
        try:
            await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
            john_context = ""
            if john_teachings:
                john_context = "\n\nEnseignements récents de John:\n" + "\n".join(f"- {t}" for t in john_teachings[-10:])
            history_context = ""
            if len(group_history) > 1:
                history_context = "\n\nContexte récent:\n" + "\n".join(f"- {m['name']}: {m['text']}" for m in group_history[-5:])
            detected = detect_language(text)
            lang_context = f"LANGUE OBLIGATOIRE: Le message est en {detected}. Tu DOIS répondre en {detected} uniquement.\n\n"
            combined_prompt = lang_context + SYSTEM_PROMPT + "\n\n" + GROUP_PROMPT + john_context + history_context
            lang_prefix = f"[{detected} only]\n"
            reply = await ask_gemini_group(combined_prompt, lang_prefix + text)
            try:
                await update.message.reply_text(reply, parse_mode="Markdown")
            except Exception:
                await update.message.reply_text(reply)
        except Exception as e:
            logger.error(f"Erreur réponse groupe: {e}")

async def on_new_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    for member in update.message.new_chat_members:
        if member.is_bot:
            continue
        if is_night_mode():
            await update.message.reply_text(
                f"🌙 Bonsoir {member.first_name} ! Bienvenue dans la communauté E-Estate !\n\n"
                f"Je suis Élise, je veille sur le groupe cette nuit 😊\n\n"
                f"Pour toutes tes questions sur E-Estate (investissement, propriétés, revenus passifs...), "
                f"écris-moi directement en message privé — je suis disponible jusqu'à 9h du matin, heure de France ! 🌙\n\n"
                f"John reprend le relais à 9h00 ☀️"
            )
        else:
            await update.message.reply_text(
                f"👋 Bonjour {member.first_name} ! Bienvenue dans le groupe E-Estate !\n\n"
                f"Je suis Élise, l'assistante de John 😊 N'hésite pas à me poser toutes tes questions sur E-Estate en message privé !"
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
        response = await asyncio.to_thread(
            groq_client.chat.completions.create,
            model=GROQ_MODEL,
            messages=[{"role": "system", "content": GROUP_PROMPT}, {"role": "user", "content": sujet}]
        )
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
        response = await asyncio.to_thread(
            groq_client.chat.completions.create,
            model=GROQ_MODEL,
            messages=[{"role": "system", "content": GROUP_PROMPT}, {"role": "user", "content": sujet}]
        )
        await bot.send_message(GROUP_ID, response.choices[0].message.content)
    except Exception as e:
        logger.error(f"Erreur formation: {e}")

async def post_quiz(bot):
    global quiz_actif, quiz_reponse, quiz_posted_time
    if quiz_actif:
        return
    sujets = [
        "Crée une question de quiz sur l'immobilier tokenisé ou la crypto avec une seule bonne réponse. Format: '🧠 QUIZ: [question] ?' suivi de '💡 Indice: [indice]'. La réponse doit être un mot ou chiffre simple. Donne aussi la réponse après '|||RÉPONSE:' (je l'extrairai, pas affichée).",
        "Crée une question de quiz sur le marché immobilier mondial avec une seule bonne réponse courte. Format: '🧠 QUIZ: [question]?' + '💡 Indice: [indice]'. Puis '|||RÉPONSE:[réponse]'.",
        "Crée une question de quiz sur la blockchain ou les cryptomonnaies. Format: '🧠 QUIZ: [question]?' + '💡 Indice: [indice]'. Puis '|||RÉPONSE:[réponse]'.",
    ]
    try:
        sujet = random.choice(sujets)
        response = await asyncio.to_thread(
            groq_client.chat.completions.create,
            model=GROQ_MODEL,
            messages=[{"role": "system", "content": GROUP_PROMPT}, {"role": "user", "content": sujet}]
        )
        texte = response.choices[0].message.content
        if "|||RÉPONSE:" in texte:
            parties = texte.split("|||RÉPONSE:")
            message = parties[0].strip()
            quiz_reponse = parties[1].strip().lower()
            quiz_actif = True
            quiz_posted_time = datetime.now()
            await bot.send_message(GROUP_ID, message + "\n\n🏆 Le premier qui répond correctement gagne le titre d'Expert du jour !\n⏰ La réponse sera révélée dans 1 heure !")
        else:
            await bot.send_message(GROUP_ID, texte)
    except Exception as e:
        logger.error(f"Erreur quiz: {e}")

async def reveal_quiz(bot):
    global quiz_actif, quiz_reponse, quiz_posted_time
    if not quiz_actif:
        return
    if (datetime.now() - quiz_posted_time).total_seconds() >= 3600:
        await bot.send_message(GROUP_ID, f"⏰ L'heure est écoulée ! Avez-vous trouvé la réponse ? 🤔\n\n✅ La réponse était : **{quiz_reponse}**\n\nBravo à ceux qui ont trouvé ! 🎉")
        quiz_actif = False
        quiz_reponse = ""

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
        response = await asyncio.to_thread(
            groq_client.chat.completions.create,
            model=GROQ_MODEL,
            messages=[{"role": "system", "content": GROUP_PROMPT}, {"role": "user", "content": sujet}]
        )
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
            response = await asyncio.to_thread(
                groq_client.chat.completions.create,
                model=GROQ_MODEL,
                messages=[{"role": "system", "content": GROUP_PROMPT}, {"role": "user", "content": msg}]
            )
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
            "⏰ *RAPPEL — Webinaire E\\-ESTATE ce soir à 21h00 \\!*\n\n"
            "🏠 Ne manque pas le Webinaire Immobilier Digital ce soir \\!\n"
            "🔗 https://meet\\.google\\.com/vqs\\-hzfs\\-qyy\n"
            "CODE : 433 091 362\\#\n\n"
            "👉 Participation gratuite \\— Invite tes proches \\!",
            parse_mode="MarkdownV2")
    except Exception as e:
        logger.error(f"Erreur rappel jeudi matin: {e}")

async def post_rappel_jeudi_soir(bot):
    try:
        await bot.send_message(GROUP_ID,
            "🔥 *DANS 1 HEURE — Webinaire E\\-ESTATE à 21h00 \\!*\n\n"
            "⚡ C'est ce soir \\! Le Webinaire commence dans 1 heure \\!\n\n"
            "🔗 https://meet\\.google\\.com/vqs\\-hzfs\\-qyy\n"
            "CODE : 433 091 362\\#\n\n"
            "🏠 Créez votre revenu passif avec l'immobilier digital \\!",
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
            "⏰ *RAPPEL — Webinaire E\\-ESTATE ce soir à 17h00 \\!*\n\n"
            "🏠 Ne manque pas le Webinaire Immobilier Digital ce soir \\!\n"
            "🔗 https://meet\\.google\\.com/rzy\\-bgok\\-mwz\n"
            "CODE : 433 091 362\\#\n\n"
            "👉 Participation gratuite \\— Invite tes proches \\!",
            parse_mode="MarkdownV2")
    except Exception as e:
        logger.error(f"Erreur rappel samedi matin: {e}")

async def post_rappel_samedi_soir(bot):
    try:
        await bot.send_message(GROUP_ID,
            "🔥 *DANS 30 MINUTES — Webinaire E\\-ESTATE à 17h00 \\!*\n\n"
            "⚡ Le Webinaire commence dans 30 minutes \\!\n\n"
            "🔗 https://meet\\.google\\.com/rzy\\-bgok\\-mwz\n"
            "CODE : 433 091 362\\#\n\n"
            "🏠 Créez votre revenu passif avec l'immobilier digital \\!",
            parse_mode="MarkdownV2")
    except Exception as e:
        logger.error(f"Erreur rappel samedi soir: {e}")

# ─── MAIN ─────────────────────────────────────────────────────────────────────
def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("reset", reset))
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, on_new_member))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & filters.ChatType.PRIVATE, handle_private_message))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & filters.ChatType.GROUPS, handle_group_message))

    async def post_init(application):
        scheduler = AsyncIOScheduler()

        scheduler.add_job(post_actualite_immo, 'cron', hour='8,20', minute=0, timezone='Europe/Paris', args=[application.bot])
        scheduler.add_job(post_formation, 'cron', hour='10,16', minute=30, timezone='Europe/Paris', args=[application.bot])
        scheduler.add_job(post_quiz, 'cron', hour='12,19', minute=0, timezone='Europe/Paris', args=[application.bot])
        scheduler.add_job(reveal_quiz, 'interval', minutes=10, args=[application.bot])
        scheduler.add_job(post_sondage, 'cron', hour=14, minute=0, timezone='Europe/Paris', args=[application.bot])
        scheduler.add_job(post_motivation, 'cron', hour=7, minute=0, timezone='Europe/Paris', args=[application.bot])
        scheduler.add_job(check_inactivite_groupe, 'interval', hours=2, args=[application.bot])

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
    app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)

if __name__ == "__main__":
    main()
