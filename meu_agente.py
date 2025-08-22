import os
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters
import google.generativeai as genai
from datetime import date # Nova importação

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

# 3. Funções de resposta do bot
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Olá! Eu sou o seu agente Alex. Estou pronto para ajudar! Como se sente hoje?"
    )

async def resposta_inteligente(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Envia a mensagem do utilizador para a IA e obtém a resposta
    try:
        resposta = model.generate_content(update.message.text)
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=resposta.text
        )
    except Exception as e:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"Desculpe, houve um erro ao processar o seu pedido: {e}"
        )

async def regista_diario(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # A mensagem do utilizador, sem o comando /diario
    texto_do_dia = ' '.join(context.args)
    
    # O prompt para o LLM
    prompt_para_ia = f"Dado este texto, extrai o humor principal. Responda apenas com o humor. Texto: {texto_do_dia}"
    
    # Obtém o humor da IA
    try:
        resposta_ia = model.generate_content(prompt_para_ia)
        humor = resposta_ia.text
    except Exception:
        humor = "Não identificado"
    
    # Escreve o registo no ficheiro
    data_hoje = date.today()
    # O 'a' significa 'append', para adicionar ao final do ficheiro sem apagar o que já lá está
    with open('diario.txt', 'a', encoding='utf-8') as f:
        f.write(f"[{data_hoje}] - Humor: {humor.strip()}\n")
        f.write(texto_do_dia + "\n\n")

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="O seu registo no diário foi guardado com sucesso!"
    )

# 4. Bloco principal para iniciar o bot
if __name__ == '__main__':
    application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    
    # Adiciona os "handlers" (os ouvintes de comandos)
    start_handler = CommandHandler('start', start)
    resposta_handler = MessageHandler(filters.TEXT & (~filters.COMMAND), resposta_inteligente)
    diario_handler = CommandHandler('diario', regista_diario) # Novo handler
    
    application.add_handler(start_handler)
    application.add_handler(resposta_handler)
    application.add_handler(diario_handler) # Novo handler
    
    print("O agente Alex está online e à escuta...")
    application.run_polling()