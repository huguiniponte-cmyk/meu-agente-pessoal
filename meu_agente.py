import os
import logging
import json
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
    MessageHandler,
    filters,
    ConversationHandler
)
import google.generativeai as genai
from datetime import date, time
from apscheduler.schedulers.asyncio import AsyncIOScheduler # Nova importação para o agendador

# Habilita o registro para ver logs de erro
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# 1. Define as chaves de API
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
if not TELEGRAM_TOKEN or not GEMINI_API_KEY:
    raise ValueError("As chaves de API do Telegram ou Gemini não foram definidas.")

# 2. Configura o modelo de IA
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

# Define os estados das conversas
PONTO_PRINCIPAL, REFLEXAO_MOMENTO, SENSACAO_CORPO, GRATIDAO, REFLEXAO_FINAL = range(5)
SOS_PENSAMENTO, SOS_EVIDENCIAS_FAVOR, SOS_EVIDENCIAS_CONTRA, SOS_PERSPECTIVA_GENTIL = range(5, 9)
ROTINA_AFIRMACAO, ROTINA_CERTEZA_CRENCA, ROTINA_CERTEZA_AVALIACAO, ROTINA_INTENCAO = range(9, 13) # Novos estados

# Define o teclado de menu principal
main_menu_keyboard = [
    ["Diário Pessoal", "SOS Mente Ansiosa"],
    ["Assistente Inteligente", "Rotina Matinal"]
]
menu_keyboard = ReplyKeyboardMarkup(main_menu_keyboard, resize_keyboard=True, one_time_keyboard=True)


# --- Funções da Nova Rotina Matinal ---

async def iniciar_rotina_matinal(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Inicia a conversa da rotina matinal."""
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Bom dia! Vamos começar o dia a fortalecer a sua identidade. Por favor, complete a frase: 'Eu sou cada vez mais...'",
        reply_markup=ReplyKeyboardRemove()
    )
    return ROTINA_AFIRMACAO

async def receber_afirmacao(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Recebe a afirmação e pergunta sobre a certeza."""
    context.user_data['afirmacao'] = update.message.text
    await update.message.reply_text(
        "Excelente. Agora, um momento de clareza. Pense numa crença ou num sentimento que tenha hoje. Qual é?"
    )
    return ROTINA_CERTEZA_CRENCA

async def receber_crenca_certeza(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Recebe a crença e pede a avaliação."""
    context.user_data['crenca_certeza'] = update.message.text
    await update.message.reply_text(
        "Numa escala de 1 (pouco certo) a 10 (muito certo), qual é o seu grau de certeza sobre isso?"
    )
    return ROTINA_CERTEZA_AVALIACAO

async def receber_avaliacao_certeza(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Recebe a avaliação e pede a intenção."""
    context.user_data['avaliacao_certeza'] = update.message.text
    await update.message.reply_text(
        "Obrigado pela reflexão. Para terminar, qual é a sua principal intenção ou foco para o dia de hoje?"
    )
    return ROTINA_INTENCAO

async def finalizar_rotina_matinal(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Recebe a intenção, guarda tudo no diário e finaliza."""
    context.user_data['intenção'] = update.message.text
    
    # Reúne os dados
    afirmacao = context.user_data.get('afirmacao')
    crenca = context.user_data.get('crenca_certeza')
    avaliacao = context.user_data.get('avaliacao_certeza')
    intencao = context.user_data.get('intenção')

    # Guarda no diário
    data_hoje = date.today()
    with open('diario.txt', 'a', encoding='utf-8') as f:
        f.write(f"--- Rotina Matinal de {data_hoje} ---\n")
        f.write(f"Afirmação: Eu sou cada vez mais {afirmacao}\n")
        f.write(f"Reflexão de Certeza: '{crenca}' (Nível: {avaliacao}/10)\n")
        f.write(f"Intenção do Dia: {intencao}\n\n")

    await update.message.reply_text(
        "Rotina matinal concluída e guardada. Que tenha um excelente dia!",
        reply_markup=menu_keyboard
    )
    context.user_data.clear()
    return ConversationHandler.END


# --- Função para a Notificação Automática ---

async def enviar_notificacao_matinal(context: ContextTypes.DEFAULT_TYPE):
    """Função que o agendador vai chamar para enviar a notificação."""
    job = context.job
    await context.bot.send_message(
        chat_id=job.chat_id,
        text="Bom dia! ✨ Clicou no botão abaixo para iniciar a sua rotina matinal?",
        reply_markup=ReplyKeyboardMarkup([["Iniciar Rotina Matinal"]], resize_keyboard=True, one_time_keyboard=True)
    )

# --- Função Start (agora guarda o seu ID) ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Guarda o chat_id para notificações e envia o menu."""
    chat_id = update.effective_chat.id
    # Guarda o seu chat_id num ficheiro para que o agente se lembre de si
    with open('user_config.json', 'w') as f:
        json.dump({'chat_id': chat_id}, f)
    
    await update.message.reply_text(
        f"Olá! Eu sou o seu agente Alex. A sua configuração foi guardada. A partir de amanhã, irei contactá-lo de manhã. O que gostaria de fazer hoje?",
        reply_markup=menu_keyboard
    )
    
# ... (Cole aqui as funções do Diário Guiado, SOS, Fim, Assistente, etc., do código anterior)
# ... (O código das outras conversas não muda)

# --- Bloco Principal (agora com o Agendador) ---
if __name__ == '__main__':
    application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    
    # Cria os Handlers das conversas
    # (conv_handler do diário, sos_conv_handler, etc., como no código anterior)
    
    # NOVO: Handler da conversa da Rotina Matinal
    rotina_matinal_handler = ConversationHandler(
        entry_points=[
            CommandHandler('bom_dia', iniciar_rotina_matinal),
            MessageHandler(filters.Regex('^Rotina Matinal$'), iniciar_rotina_matinal),
            MessageHandler(filters.Regex('^Iniciar Rotina Matinal$'), iniciar_rotina_matinal)
        ],
        states={
            ROTINA_AFIRMACAO: [MessageHandler(filters.TEXT & ~filters.COMMAND, receber_afirmacao)],
            ROTINA_CERTEZA_CRENCA: [MessageHandler(filters.TEXT & ~filters.COMMAND, receber_crenca_certeza)],
            ROTINA_CERTEZA_AVALIACAO: [MessageHandler(filters.TEXT & ~filters.COMMAND, receber_avaliacao_certeza)],
            ROTINA_INTENCAO: [MessageHandler(filters.TEXT & ~filters.COMMAND, finalizar_rotina_matinal)],
        },
        fallbacks=[CommandHandler('fim', fim)],
    )

    # Adiciona todos os handlers à aplicação
    application.add_handler(CommandHandler('start', start))
    # application.add_handler(diario_conv_handler) # Adicione os outros handlers aqui
    # application.add_handler(sos_conv_handler)
    application.add_handler(rotina_matinal_handler) # NOVO
    # application.add_handler(MessageHandler(filters.Regex('^Assistente Inteligente$'), assistente_inteligente))
    # application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, resposta_inteligente))

    # --- Configuração do Agendador ---
    scheduler = AsyncIOScheduler()
    
    # Tenta carregar o chat_id guardado para agendar a tarefa
    try:
        with open('user_config.json', 'r') as f:
            config = json.load(f)
            chat_id = config.get('chat_id')
            if chat_id:
                # Agendador para enviar a notificação todos os dias às 8:00
                scheduler.add_job(enviar_notificacao_matinal, 'cron', hour=8, minute=0, chat_id=chat_id, context=application)
                print(f"Notificação matinal agendada para o chat_id: {chat_id}")
    except FileNotFoundError:
        print("Ficheiro de configuração não encontrado. O utilizador precisa de enviar /start primeiro.")

    scheduler.start()
    
    print("O agente Alex está online e à escuta...")
    application.run_polling()
