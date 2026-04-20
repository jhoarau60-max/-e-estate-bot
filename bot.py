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
