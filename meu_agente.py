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
# APScheduler já não é necessário, o próprio bot tem um agendador
# from apscheduler.schedulers.asyncio import AsyncIOScheduler

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

# 3. Define os "estados" de todas as conversas
PONTO_PRINCIPAL, REFLEXAO_MOMENTO, SENSACAO_CORPO, GRATIDAO, REFLEXAO_FINAL = range(5)
SOS_PENSAMENTO, SOS_EVIDENCIAS_FAVOR, SOS_EVIDENCIAS_CONTRA, SOS_PERSPECTIVA_GENTIL = range(5, 9)
ROTINA_AFIRMACAO, ROTINA_CERTEZA_CRENCA, ROTINA_CERTEZA_AVALIACAO, ROTINA_INTENCAO = range(9, 13)

# 4. Define o teclado de menu principal
main_menu_keyboard = [
    ["Diário Pessoal", "SOS Mente Ansiosa"],
    ["Assistente Inteligente", "Rotina Matinal"]
]
menu_keyboard = ReplyKeyboardMarkup(main_menu_keyboard, resize_keyboard=True, one_time_keyboard=True)

# --- Funções da Rotina Matinal ---

async def iniciar_rotina_matinal(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Bom dia! Vamos começar o dia a fortalecer a sua identidade. Por favor, complete a frase: 'Eu sou cada vez mais...'",
        reply_markup=ReplyKeyboardRemove()
    )
    return ROTINA_AFIRMACAO

async def receber_afirmacao(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['afirmacao'] = update.message.text
    await update.message.reply_text("Excelente. Agora, um momento de clareza. Pense numa crença ou num sentimento que tenha hoje. Qual é?")
    return ROTINA_CERTEZA_CRENCA

async def receber_crenca_certeza(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['crenca_certeza'] = update.message.text
    await update.message.reply_text("Numa escala de 1 (pouco certo) a 10 (muito certo), qual é o seu grau de certeza sobre isso?")
    return ROTINA_CERTEZA_AVALIACAO

async def receber_avaliacao_certeza(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['avaliacao_certeza'] = update.message.text
    await update.message.reply_text("Obrigado pela reflexão. Para terminar, qual é a sua principal intenção ou foco para o dia de hoje?")
    return ROTINA_INTENCAO

async def finalizar_rotina_matinal(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['intenção'] = update.message.text
    
    afirmacao = context.user_data.get('afirmacao', 'N/A')
    crenca = context.user_data.get('crenca_certeza', 'N/A')
    avaliacao = context.user_data.get('avaliacao_certeza', 'N/A')
    intencao = context.user_data.get('intenção', 'N/A')

    data_hoje = date.today()
    with open('diario.txt', 'a', encoding='utf-8') as f:
        f.write(f"--- Rotina Matinal de {data_hoje} ---\n")
        f.write(f"Afirmação: Eu sou cada vez mais {afirmacao}\n")
        f.write(f"Reflexão de Certeza: '{crenca}' (Nível: {avaliacao}/10)\n")
        f.write(f"Intenção do Dia: {intencao}\n\n")

    await update.message.reply_text("Rotina matinal concluída e guardada. Que tenha um excelente dia!", reply_markup=menu_keyboard)
    context.user_data.clear()
    return ConversationHandler.END


# --- Funções de Notificação ---

async def enviar_notificacao_matinal(context: ContextTypes.DEFAULT_TYPE):
    try:
        with open('user_config.json', 'r') as f:
            config = json.load(f)
            chat_id = config.get('chat_id')
            if chat_id:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text="Bom dia! ✨ Clique no botão abaixo para iniciar a sua rotina matinal.",
                    reply_markup=ReplyKeyboardMarkup([["Iniciar Rotina Matinal"]], resize_keyboard=True, one_time_keyboard=True)
                )
    except FileNotFoundError:
        logging.warning("Ficheiro de configuração não encontrado. O utilizador precisa de enviar /start primeiro.")
    
async def post_init(application: ApplicationBuilder) -> None:
    """Função chamada depois do bot ser inicializado."""
    try:
        with open('user_config.json', 'r') as f:
            config = json.load(f)
            chat_id = config.get('chat_id')
            if chat_id:
                # Agendador para enviar a notificação todos os dias às 8:00
                application.job_queue.run_daily(
                    enviar_notificacao_matinal,
                    time=time(hour=8, minute=0),
                    job_kwargs={'chat_id': chat_id},
                )
                logging.info(f"Notificação matinal agendada para o chat_id: {chat_id} às 08:00.")
    except FileNotFoundError:
        logging.warning("Ficheiro de configuração não encontrado. O utilizador precisa de enviar /start primeiro.")


# --- Funções Gerais ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    try:
        with open('user_config.json', 'w') as f:
            json.dump({'chat_id': chat_id}, f)
        await update.message.reply_text(
            f"Olá! Eu sou o seu agente Alex. A sua configuração foi guardada. A partir de amanhã, irei contactá-lo de manhã. O que gostaria de fazer hoje?",
            reply_markup=menu_keyboard
        )
    except Exception as e:
        logging.error(f"Erro ao guardar user_config.json: {e}")
        await update.message.reply_text("Olá! Tive um problema a guardar a sua configuração, mas pode usar o menu.", reply_markup=menu_keyboard)

async def fim(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Processo cancelado. A regressar ao menu principal.", reply_markup=menu_keyboard)
    if 'user_data' in context:
        context.user_data.clear()
    return ConversationHandler.END

# --- Funções do Diário Guiado (mantidas do código anterior) ---
async def iniciar_diario_guiado(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        "Olá! Vamos fazer uma pequena viagem pelo seu dia. Para começar, qual foi o momento ou sentimento principal de hoje?",
        reply_markup=ReplyKeyboardRemove()
    )
    return PONTO_PRINCIPAL

async def receber_ponto_principal(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    texto_inicial = update.message.text
    context.user_data['ponto_principal'] = texto_inicial
    prompt_para_ia = f"A pessoa disse que o ponto principal do dia dela foi: '{texto_inicial}'. Faça uma pergunta aberta e empática para aprofundar este sentimento ou momento."
    try:
        resposta_ia = model.generate_content(prompt_para_ia)
        proxima_pergunta = resposta_ia.text
    except Exception:
        proxima_pergunta = "Interessante. E como é que isso o fez sentir?"

    await update.message.reply_text(proxima_pergunta)
    return REFLEXAO_MOMENTO

async def receber_reflexao_momento(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    texto_reflexao = update.message.text
    context.user_data['reflexao_momento'] = texto_reflexao
    await update.message.reply_text("Obrigado pela partilha. E como se sentiu no seu corpo hoje? Notou alguma tensão, energia ou cansaço?")
    return SENSACAO_CORPO

async def receber_sensacao_corpo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    texto_corpo = update.message.text
    context.user_data['sensacao_corpo'] = texto_corpo
    await update.message.reply_text("Entendido. Agora, para focar no positivo, há uma pequena coisa pela qual se sente grato hoje?")
    return GRATIDAO

async def receber_gratidao(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    texto_gratidao = update.message.text
    context.user_data['gratidao'] = texto_gratidao
    await update.message.reply_text("Ótimo. Para terminar, há algo mais que queira registar ou um sentimento final sobre o dia de hoje?")
    return REFLEXAO_FINAL

async def guardar_e_finalizar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    texto_final = update.message.text
    ponto_principal = context.user_data.get('ponto_principal', 'N/A')
    reflexao_momento = context.user_data.get('reflexao_momento', 'N/A')
    sensacao_corpo = context.user_data.get('sensacao_corpo', 'N/A')
    gratidao = context.user_data.get('gratidao', 'N/A')
    prompt_resumo = f"""
    Você é um curador de almas e um observador racional. Seu objetivo é criar um registo de diário que transforme a experiência emocional do usuário numa narrativa clara, estruturada e construtiva. Use uma linguagem calma e objetiva. Evite emoções e foco-se em causa, efeito e lições aprendidas. Não se refira a si mesmo como IA ou robô.
    Dados:
    - Ponto Principal do Dia: {ponto_principal}
    - Reflexão Aprofundada: {reflexao_momento}
    - Conexão Corpo-Mente: {sensacao_corpo}
    - Nota de Gratidão: {gratidao}
    - Conclusão Final: {texto_final}
    Transforme estes dados num registo de diário estoico, com títulos para cada secção.
    """
    try:
        resposta_ia = model.generate_content(prompt_resumo)
        resumo_final = resposta_ia.text
    except Exception:
        resumo_final = f"Ponto Principal: {ponto_principal}\nReflexão: {reflexao_momento}\nCorpo: {sensacao_corpo}\nGratidão: {gratidao}\nConclusão: {texto_final}"

    data_hoje = date.today()
    with open('diario.txt', 'a', encoding='utf-8') as f:
        f.write(f"--- Registo de {data_hoje} ---\n")
        f.write(resumo_final + "\n\n")

    await update.message.reply_text("A sua viagem pelo dia de hoje foi guardada com sucesso. Bom descanso!", reply_markup=menu_keyboard)
    context.user_data.clear()
    return ConversationHandler.END

# --- Funções do Módulo SOS (mantidas do código anterior) ---
async def iniciar_sos(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        "Módulo SOS ativado. Por favor, partilhe o pensamento negativo ou ansioso que gostaria de analisar.",
        reply_markup=ReplyKeyboardRemove()
    )
    return SOS_PENSAMENTO

async def receber_pensamento_sos(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    pensamento = update.message.text
    context.user_data['pensamento_original'] = pensamento
    
    await update.message.reply_text(
        "Obrigado por partilhar. Vamos analisar isso. "
        "Que evidências factuais sustentam que esse pensamento é 100% verdade?"
    )
    return SOS_EVIDENCIAS_FAVOR

async def receber_evidencias_favor(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    evidencias_favor = update.message.text
    context.user_data['evidencias_favor'] = evidencias_favor
    
    await update.message.reply_text(
        "Entendido. Agora, que evidências sustentam que esse pensamento pode não ser inteiramente verdade?"
    )
    return SOS_EVIDENCIAS_CONTRA

async def receber_evidencias_contra(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    evidencias_contra = update.message.text
    context.user_data['evidencias_contra'] = evidencias_contra
    
    await update.message.reply_text(
        "Ótima reflexão. Para terminar, se fosse gentil consigo mesmo, como reformularia esse pensamento de uma maneira mais equilibrada e realista?"
    )
    return SOS_PERSPECTIVA_GENTIL

async def finalizar_sos(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    perspectiva_gentil = update.message.text
    
    pensamento_original = context.user_data.get('pensamento_original')
    evidencias_favor = context.user_data.get('evidencias_favor')
    evidencias_contra = context.user_data.get('evidencias_contra')

    prompt_resumo_sos = f"""
    Você é um observador racional. O usuário realizou um exercício de reestruturação cognitiva sobre um pensamento negativo.
    - Pensamento Original: "{pensamento_original}"
    - Evidências a Favor: "{evidencias_favor}"
    - Evidências Contra: "{evidencias_contra}"
    - Reformulação Construtiva do Usuário: "{perspectiva_gentil}"

    Crie um resumo objetivo e estruturado deste exercício, focando na lógica e na nova perspetiva alcançada. Termine com a reformulação do usuário como a conclusão principal.
    """
    
    try:
        resposta_ia = model.generate_content(prompt_resumo_sos)
        resumo_final = resposta_ia.text
    except Exception:
        resumo_final = f"Exercício SOS:\nPensamento: {pensamento_original}\nNova Perspetiva: {perspectiva_gentil}"
    
    data_hoje = date.today()
    with open('diario.txt', 'a', encoding='utf-8') as f:
        f.write(f"--- Exercício SOS de {data_hoje} ---\n")
        f.write(resumo_final + "\n\n")

    await update.message.reply_text(
        "Exercício concluído e guardado no seu diário. Lembre-se, você tem o poder de questionar os seus pensamentos.",
        reply_markup=menu_keyboard
    )
    context.user_data.clear()
    return ConversationHandler.END

# --- Funções do Assistente Inteligente ---
async def assistente_inteligente(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Estou pronto para responder a qualquer pergunta. Em que posso ajudar?", reply_markup=ReplyKeyboardRemove())

async def resposta_inteligente(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        resposta = model.generate_content(update.message.text)
        await context.bot.send_message(chat_id=update.effective_chat.id, text=resposta.text, reply_markup=menu_keyboard)
    except Exception as e:
        await context.bot.send_message(chat_id=update.effective_chat.id, text=f"Desculpe, houve um erro ao processar o seu pedido: {e}", reply_markup=menu_keyboard)

# --- Bloco Principal ---
if __name__ == '__main__':
    application = ApplicationBuilder().token(TELEGRAM_TOKEN).post_init(post_init).build()
    
    diario_conv_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex('^Diário Pessoal$'), iniciar_diario_guiado)],
        states={
            PONTO_PRINCIPAL: [MessageHandler(filters.TEXT & ~filters.COMMAND, receber_ponto_principal)],
            REFLEXAO_MOMENTO: [MessageHandler(filters.TEXT & ~filters.COMMAND, receber_reflexao_momento)],
            SENSACAO_CORPO: [MessageHandler(filters.TEXT & ~filters.COMMAND, receber_sensacao_corpo)],
            GRATIDAO: [MessageHandler(filters.TEXT & ~filters.COMMAND, receber_gratidao)],
            REFLEXAO_FINAL: [MessageHandler(filters.TEXT & ~filters.COMMAND, guardar_e_finalizar)],
        },
        fallbacks=[CommandHandler('fim', fim)],
    )

    sos_conv_handler = ConversationHandler(
        entry_points=[CommandHandler('sos', iniciar_sos), MessageHandler(filters.Regex('^SOS Mente Ansiosa$'), iniciar_sos)],
        states={
            SOS_PENSAMENTO: [MessageHandler(filters.TEXT & ~filters.COMMAND, receber_pensamento_sos)],
            SOS_EVIDENCIAS_FAVOR: [MessageHandler(filters.TEXT & ~filters.COMMAND, receber_evidencias_favor)],
            SOS_EVIDENCIAS_CONTRA: [MessageHandler(filters.TEXT & ~filters.COMMAND, receber_evidencias_contra)],
            SOS_PERSPECTIVA_GENTIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, finalizar_sos)],
        },
        fallbacks=[CommandHandler('fim', fim)],
    )

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

    application.add_handler(CommandHandler('start', start))
    application.add_handler(diario_conv_handler)
    application.add_handler(sos_conv_handler)
    application.add_handler(rotina_matinal_handler)
    application.add_handler(MessageHandler(filters.Regex('^Assistente Inteligente$'), assistente_inteligente))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, resposta_inteligente))
    
    print("O agente Alex está online e à escuta...")
    application.run_polling()
