from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
import datetime
import time
import logging
from flask import Flask
from threading import Thread
import os
import textwrap
import json
from keep_alive import keep_alive

keep_alive()  # Lance le serveur Flask pour Render/UptimeRobot

logging.basicConfig(level=logging.INFO)
# === FONCTIONS ADMIN ===

OWNER_ID = 7350223087

ADMIN_FILE = 'admins.json'

# Fonction pour charger la liste des admins à partir du fichier JSON
def load_admins():
    try:
        with open(ADMIN_FILE, "r") as f:
            admins = json.load(f)
            logging.info(f"IDs des admins chargés : {admins}")
            return admins
    except FileNotFoundError:
        logging.info("Fichier admins.json non trouvé")
        return []

# Fonction pour sauvegarder la liste des admins dans le fichier JSON
def save_admins(admins):
    with open(ADMIN_FILE, "w") as f:
        json.dump(admins, f)

# Vérifier si un utilisateur est admin
def is_admin(user_id):
    admins = load_admins()
    return user_id in admins

# === CONFIG FLASK POUR UPTIME ROBOT ===
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot actif!"

def run_flask():
    app.run(host='0.0.0.0', port=8080)

# === CONFIG BOT ===
TOKEN = os.environ['BOT_TOKEN']  # Clé d'environnement sur Render
ADMIN_ID = int(os.environ['ADMIN_ID'])  # Clé d'environnement sur Render
CHANNEL_ID = os.environ['CHANNEL_ID']  # Clé d'environnement sur Render
FICHIER_COMMANDES = 'commandes.txt'
FICHIER_COMMANDES_TERMINEES = 'commandes_terminees.txt'

# === CHARGER LES COMMANDES DÉJÀ SAUVEGARDÉES ===
commandes_stockees = []
commandes_terminees = []

if os.path.exists(FICHIER_COMMANDES):
    with open(FICHIER_COMMANDES, 'r', encoding='utf-8') as f:
        commandes_stockees = f.read().split("\n\n")

if os.path.exists(FICHIER_COMMANDES_TERMINEES):
    with open(FICHIER_COMMANDES_TERMINEES, 'r', encoding='utf-8') as f:
        commandes_terminees = f.read().split("\n\n")

# === PRODUITS ===
products = [
    {"name": "Manteau 1 Adidas", "photo": "https://via.placeholder.com/150"},
    {"name": "Manteau 2 Nike", "photo": "https://via.placeholder.com/150"},
    {"name": "Manteau 3 Puma", "photo": "https://via.placeholder.com/150"},
    {"name": "Chaussure 1 Nike", "photo": "https://via.placeholder.com/150"},
    {"name": "Chaussure 2 Adidas", "photo": "https://via.placeholder.com/150"},
    {"name": "T-shirt 1 Supreme", "photo": "https://via.placeholder.com/150"}
]

# === CONFIGURATION DES LOGS ===
logging.basicConfig(filename='bot_log.log', level=logging.INFO, format='%(asctime)s - %(message)s')

# === FONCTIONS BOT ===
async def get_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    await update.message.reply_text(f"Ton ID Telegram est : {user_id}")

async def handle_voir_mon_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    await query.edit_message_text(
        f"Ton ID Telegram est : {user_id}",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Retour au menu", callback_data="menu")]])
    )

async def handle_ajouter_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "Utilise la commande suivante dans le chat :\n\n`/addadmin <user_id>`",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Retour au menu", callback_data="menu")]])
    )

async def handle_retirer_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    if not is_admin(user_id):
        await query.edit_message_text("Vous n'avez pas la permission de faire ça.")
        return

    await query.edit_message_text("Entrez l'ID de l'admin à retirer (ou annulez pour revenir au menu) :\n\nExemple : /removeadmin <user_id>", 
                                 reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Annuler", callback_data="menu")]]))

    context.user_data["awaiting_remove_admin"] = True

async def add_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("Tu n'es pas autorisé à ajouter un admin.")
        return

    if not context.args:
        await update.message.reply_text("Utilisation : /addadmin <user_id>")
        return

    new_admin_id = int(context.args[0])
    admins = load_admins()
    if new_admin_id in admins:
        await update.message.reply_text("Cet utilisateur est déjà admin.")
    else:
        admins.append(new_admin_id)
        save_admins(admins)
        await update.message.reply_text(f"L'utilisateur {new_admin_id} est maintenant admin.")

async def remove_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("Tu n'es pas autorisé à retirer un admin.")
        return

    if not context.args:
        await update.message.reply_text("Utilisation : /removeadmin <user_id>")
        return

    remove_id = int(context.args[0])
    admins = load_admins()
    if remove_id not in admins:
        await update.message.reply_text("Cet utilisateur n’est pas admin.")
    else:
        admins.remove(remove_id)
        save_admins(admins)
        await update.message.reply_text(f"L'utilisateur {remove_id} a été retiré des admins.")

async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Voir les prix", callback_data="prix")],
        [InlineKeyboardButton("Voir les produits", callback_data="produits")],
        [InlineKeyboardButton("Passer une commande", callback_data="commande")],
        [InlineKeyboardButton("Voir ma commande", callback_data="ma_commande")],
        [InlineKeyboardButton("get id", callback_data="voir_mon_id")]
    ]
    user_id = update.effective_user.id if update.message else update.callback_query.from_user.id
    if is_admin(user_id):
        keyboard.append([InlineKeyboardButton("Liste des admins", callback_data="list_admins")])
        keyboard.append([InlineKeyboardButton("Ajouter un admin", callback_data="ajouter_admin")])
        keyboard.append([InlineKeyboardButton("Retirer un admin", callback_data="retirer_admin")])
        keyboard.append([InlineKeyboardButton("Voir les commandes", callback_data="view_orders")])
        keyboard.append([InlineKeyboardButton("Voir les commandes terminées", callback_data="view_completed_orders")])

    reply_markup = InlineKeyboardMarkup(keyboard)

    try:
        if update.callback_query:
            await update.callback_query.message.edit_text("Menu principal :", reply_markup=reply_markup)
        elif update.message:
            await update.message.reply_text("Menu principal :", reply_markup=reply_markup)
    except Exception as e:
        logging.error(f"Erreur lors de l'affichage du menu : {e}")
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Menu principal :", reply_markup=reply_markup)
async def handle_list_admins(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    admins = load_admins()
    if not admins:
        await query.edit_message_text("Aucun admin enregistré.")
    else:
        message = "Liste des admins :\n\n"
        for admin_id in admins:
            try:
                user = await context.bot.get_chat(admin_id)
                name = user.full_name
                tag = f"@{user.username}" if user.username else ""
                message += f"- {name} {tag} ('{admin_id}')\n"
            except Exception as e:
                message += f"- (Utilisateur inconnu) ('{admin_id}')\n"

        await query.edit_message_text(message, reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Retour au menu", callback_data="menu")]
        ]))
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await show_main_menu(update, context)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "Voici ce que tu peux faire avec ce bot :\n\n"
        "- /start : Afficher le menu principal\n"
        "- Voir les prix : Affiche la liste des prix\n"
        "- Voir les produits : Montre les photos\n"
        "- Passer une commande : Envoie ta commande manuellement\n"
        "- Marquer une commande comme terminée : Marque la commande comme faite\n"
        "- Retour au menu : Ramène au menu principal\n"
    )
    await update.message.reply_text(text)

async def handle_prices(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    message = textwrap.dedent("""Disponible(Available)

Weed ❌
Hash ❌
Waxpen ❌
Lean ❌
Poud❌
E ❌
Md ❌
Bonbon(speed) ❌
Champignon (mush)❌
Acide(lsd) ❌
Edible ❌
Ket ❌
Pods 50mg nico❌
PopSicle❌
Puff bars ❌
Shatter ❌
Wax ❌
Backwood ❌
Pods de wax ❌
Xan ❌
Perc (percocet « press »)❌
Perc pharma ❌
Diamond thc ❌
Cannalean banane ❌
Papier saveur ❌
Adderall ❌



Prix
Weed
3.5 à 20$
7 à 40$
14 à 75$
Oz à 120$
2oz à 210$
Qp à 420$
Demi L à 750$

|_____—_____|

H
1g 10$
10g 90$
20g 175$
28g 240$
4oz 840$

H lithium
1g 15$
3g 40$
7g 85$
14g 165$
28g 310$

|_____—_____|

Lean
1bouteil 100$
2 190$
3 270$
4 340$
5 400$
10 700$

Cannalean banane
1 45$
2 80$
3 120$
4 160$
5  195$
10 380$
20 720$

|_____—_____|

Waxpen
1waxpen 45$
2waxpen 90$
3waxpen 130$
5waxpen 210$
8waxpen 325$
10waxpren 395$

Waxpen icarus 2.1g 
1 60$
2 120$
3 170$
5 250$

|_____—_____|
« Demi complète 
.5 60$ 
1g 120$ »
|_____—_____|
Pou
1 demi 40$
2 demi 80$
3 demi 115$
4 demi 150$
5 demi 185$
7 demi 255$
9 demi 325$
10 demi 360$
16 demi 545$
|_____—_____|

Ket
1 demi 35$
2 demi 70$
3 demi 100$
7 demi 210$

Acide((double)lsd)
1 20$
4 75$
5 90$
10 170$

Edible
1 25$
5 115$
10 220$

PopSicle
1 25$
10 200$

Md
1pils=0.1g
0.1g 10$
1g 100$
2g 190$
3.5g 330$
7g 630$
10$ 850$
20g 1500$
28g 1950$

Shatter/wax
1 25$
3 70$
5 115$
10 210$$

Pods 50mg nico
1 pour 20$
3 pour 55$

Mush
3.5g 30$
7g 55$
14g 85$
1oz 130$

|_____—_____|
Puff bar vice
25$ chaque
|_____—_____|
Puff bar 5000 puff
1 30$
5 125$
|_____—_____|

Backwood
1 25$
Banane 35$

Pods de wax
1 80$
3 235$
5 385$
10 750$

Xan
10$ 1
25$ 3
45$ 6
70$ 10
135$ 20
260$ 40
325$ 50
600$ 100

|_____—_____|
Perc pharma
1.5$ le mg
|_____—_____|
Perc
15$ la pils
30$ 2
60$ 4
75$ 5
140$ 10
270$ 20
520$ 40
640$ 50
1260$ 100
|_____—_____|

Diamond thc
50$ 1
100$ 2
225$ 5

Papier à saveur
8$ chaque

Bonbon(speed)
5 20$
10 40$
20 80$
25 100$
""")

    # Diviser le message si nécessaire pour Telegram
    max_message_length = 4096
    while len(message) > max_message_length:
        await query.edit_message_text(message[:max_message_length])
        message = message[max_message_length:]

    # Envoyer le reste du message
    await query.edit_message_text(message)

    keyboard = [[InlineKeyboardButton("Retour au menu", callback_data="menu")]]
    await query.edit_message_text(text=message, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

async def handle_products(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    for p in products:
        await context.bot.send_photo(
            chat_id=query.message.chat.id,
            photo=p["photo"],
            caption=p["name"]
        )

    keyboard = [[InlineKeyboardButton("Retour au menu", callback_data="menu")]]
    await context.bot.send_message(chat_id=query.message.chat.id, text="Voici les produits :", reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data["awaiting_order"] = True

    text = (
        "Remplis ta commande en répondant dans ce format :\n\n"
        "Produit:...\n"
        "Quantité:...\n"
        "Nom:...\n"
        "Téléphone:...\n"
        "Adresse:..."
    )
    keyboard = [[InlineKeyboardButton("Retour au menu", callback_data="menu")]]
    await query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get("awaiting_remove_admin"):
        user_id = update.effective_user.id
        if not is_admin(user_id):
            await update.message.reply_text("Vous n'avez pas la permission de faire ça.")
            return

        try:
            remove_id = int(update.message.text)
        except ValueError:
            await update.message.reply_text("ID invalide. Veuillez entrer un nombre.")
            return

        # Empêcher de retirer l'OWNER_ID
        if remove_id == OWNER_ID:
            await update.message.reply_text("Impossible de retirer l'admin principal.")
            return

        admins = load_admins()
        if remove_id in admins:
            admins.remove(remove_id)
            save_admins(admins)
            await update.message.reply_text(f"L'utilisateur {remove_id} a été retiré des admins.")
        else:
            await update.message.reply_text("Cet utilisateur n'est pas un admin.")

        context.user_data["awaiting_remove_admin"] = False
        await show_main_menu(update, context)
    elif context.user_data.get("awaiting_order"):
        commande = update.message.text
        user_id = update.effective_user.id
        if user_id not in commandes_utilisateurs:
            commandes_utilisateurs[user_id] = []
        commandes_utilisateurs[user_id].append(commande)
        commandes_stockees.append(commande)
        with open(FICHIER_COMMANDES, 'w', encoding='utf-8') as f:
            f.write("\n\n".join(commandes_stockees))
        user_file = f"commandes_{user_id}.txt"
        with open(user_file, 'w', encoding='utf-8') as f:
            f.write(commande)
        await context.bot.send_message(chat_id=CHANNEL_ID, text=commande)
        await update.message.reply_text("Commande sauvegardée avec succès!")
        context.user_data["awaiting_order"] = False
        await show_main_menu(update, context)
    else:
        # Votre logique pour les messages normaux
        pass

async def handle_user_order_view(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    # Vérifier si l'utilisateur a des commandes enregistrées dans le dictionnaire
    if user_id in commandes_utilisateurs:
        commande = commandes_utilisateurs[user_id][-1]
        await query.edit_message_text(f"Ta commande :\n\n{commande}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Retour au menu", callback_data="menu")]]))
    else:
        # Vérifier si l'utilisateur a un fichier de commande associé
        user_file = f"commandes_{query.from_user.id}.txt"
        if os.path.exists(user_file):
            with open(user_file, 'r', encoding='utf-8') as f:
                commande = f.read()
            if commande in commandes_terminees:
                await query.edit_message_text("Tu n’as encore passé aucune commande.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Retour au menu", callback_data="menu")]]))
            else:
                commande_num = len(commandes_stockees) - commandes_stockees[::-1].index(commande)
                await query.edit_message_text(f"Ta commande n°{commande_num} :\n\n{commande}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Retour au menu", callback_data="menu")]]))
        else:
            await query.edit_message_text("Tu n’as encore passé aucune commande.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Retour au menu", callback_data="menu")]]))
async def handle_view_orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    if not is_admin(user_id):
        await query.answer("Non autorisé.")
        return

    await query.answer()
    if not commandes_stockees:
        keyboard = [[InlineKeyboardButton("Retour au menu", callback_data="menu")]]
        await query.edit_message_text("Aucune commande pour l’instant.", reply_markup=InlineKeyboardMarkup(keyboard))
        return

    commandes_text = ""
    for i, commande in enumerate(commandes_stockees):
        commandes_text += f"Commande n°{i+1} :\n{commande}\n\n"
    keyboard = [[InlineKeyboardButton("Retour au menu principal", callback_data="menu")],
                [InlineKeyboardButton("Voir les commandes terminées", callback_data="view_completed_orders")]]
    for i, commande in enumerate(commandes_stockees[-10:]):
        if commande.strip():
            keyboard.append([InlineKeyboardButton(f"Marquer commande {i+1} comme terminée", callback_data=f"complete_order_{i}")])
    await query.edit_message_text(f"Dernières commandes :\n\n{commandes_text}", reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_view_completed_orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    if not is_admin(user_id):
        await query.answer("Non autorisé.")
        return

    await query.answer()
    if not commandes_terminees:
        await query.edit_message_text("Aucune commande terminée pour l’instant.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Retour au menu", callback_data="menu")]]))
    else:
        commandes_text = ""
        for i, commande in enumerate(commandes_terminees):
            commandes_text += f"Commande n°{i+1} :\n{commande}\n\n"
        keyboard = [[InlineKeyboardButton("Retour au menu principal", callback_data="menu")],
                    [InlineKeyboardButton("Voir les commandes", callback_data="view_orders")]]
        await query.edit_message_text(f"Commandes terminées :\n\n{commandes_text}", reply_markup=InlineKeyboardMarkup(keyboard))
async def handle_complete_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    index = int(query.data.split("_")[-1])

    commande_terminee = commandes_stockees.pop(index)
    commandes_terminees.append(commande_terminee)

    with open(FICHIER_COMMANDES_TERMINEES, 'a', encoding='utf-8') as f:
        f.write(commande_terminee + "\n\n")

    with open(FICHIER_COMMANDES, 'w', encoding='utf-8') as f:
        f.write("\n\n".join(commandes_stockees))

    await query.answer(f"Commande {index + 1} marquée comme terminée.")
    await handle_view_orders(update, context)

# === FONCTIONS DE GESTION DES COMMANDES ===

def sauvegarder_commande(commande):
    with open(FICHIER_COMMANDES, 'a', encoding='utf-8') as f:
        f.write(commande + "\n\n")

def charger_commandes():
    if os.path.exists(FICHIER_COMMANDES):
        with open(FICHIER_COMMANDES, 'r', encoding='utf-8') as f:
            return f.read().split("\n\n")
    else:
        return []

def sauvegarder_commande_terminee(commande):
    with open(FICHIER_COMMANDES_TERMINEES, 'a', encoding='utf-8') as f:
        f.write(commande + "\n\n")

def charger_commandes_terminees():
    if os.path.exists(FICHIER_COMMANDES_TERMINEES):
        with open(FICHIER_COMMANDES_TERMINEES, 'r', encoding='utf-8') as f:
            return f.read().split("\n\n")
    else:
        return []

# === FONCTIONS DE GESTION DES ADMINS ===

def sauvegarder_admin(admin_id):
    admins = load_admins()
    admins.append(admin_id)
    save_admins(admins)

def charger_admins():
    return load_admins()

# === FONCTIONS DE GESTION DES PRODUITS ===

def sauvegarder_produit(produit):
    products.append(produit)

def charger_produits():
    return products

# === LANCEMENT DU BOT ===

def run_bot():
    try:
        application = Application.builder().token(TOKEN).build()

        application.add_handler(CommandHandler("id", get_id))
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CallbackQueryHandler(handle_view_orders, pattern="view_orders"))
        application.add_handler(CallbackQueryHandler(handle_view_completed_orders, pattern="view_completed_orders"))
        application.add_handler(CallbackQueryHandler(handle_complete_order, pattern="complete_order_"))
        application.add_handler(CallbackQueryHandler(handle_prices, pattern="prix"))
        application.add_handler(CallbackQueryHandler(handle_products, pattern="produits"))
        application.add_handler(CallbackQueryHandler(handle_order, pattern="commande"))
        application.add_handler(CallbackQueryHandler(show_main_menu, pattern="menu"))
        application.add_handler(CallbackQueryHandler(handle_user_order_view, pattern="ma_commande"))
        application.add_handler(CallbackQueryHandler(handle_voir_mon_id, pattern="voir_mon_id"))
        application.add_handler(CallbackQueryHandler(handle_ajouter_admin, pattern="ajouter_admin"))
        application.add_handler(CallbackQueryHandler(handle_retirer_admin, pattern="retirer_admin"))
        application.add_handler(CommandHandler("addadmin", add_admin))
        application.add_handler(CommandHandler("removeadmin", remove_admin))
        application.add_handler(CallbackQueryHandler(handle_list_admins, pattern="list_admins"))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_messages))
        logging.info("Bot démarré en mode long polling...")
        application.run_polling(timeout=86400, drop_pending_updates=True)
    except Exception as e:
        logging.error(f"Erreur lors du démarrage du bot : {e}")
        time.sleep(5)
        run_bot()

# === MAIN ===

if __name__ == '__main__':
    Thread(target=run_flask).start()
    run_bot()
