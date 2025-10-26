import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import google.generativeai as genai

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Configuration
TELEGRAM_BOT_TOKEN = "8180132074:AAFxr6oCd8KTtW87Equyc0V-K6urqSR9sJ4"
GEMINI_API_KEY = "AIzaSyARl_L6juQqp7l994M6xWxWHHQHVJcxHcA"

# Configure Gemini API
genai.configure(api_key=GEMINI_API_KEY)

# Configure generation settings with token limits
generation_config = {
    "temperature": 0.9,
    "top_p": 1,
    "top_k": 1,
    "max_output_tokens": 2048,
}

# Use Gemini 2.5 Flash (fast and free)
model = genai.GenerativeModel('gemini-2.5-flash', generation_config=generation_config)

# Store conversation history per user
user_conversations = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a message when the command /start is issued."""
    user_id = update.effective_user.id
    user_conversations[user_id] = model.start_chat(history=[])
    
    await update.message.reply_text(
        "👋 Hello! I'm an AI assistant powered by Google Gemini.\n\n"
        "Send me any message and I'll respond intelligently!\n\n"
        "Commands:\n"
        "/start - Start a new conversation\n"
        "/clear - Clear conversation history\n"
        "/help - Show this help message"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a message when the command /help is issued."""
    await update.message.reply_text(
        "🤖 AI Telegram Bot Help\n\n"
        "Just send me any text message and I'll respond using Google Gemini AI.\n\n"
        "Available commands:\n"
        "/start - Start a new conversation\n"
        "/clear - Clear your conversation history\n"
        "/help - Show this help message\n\n"
        "I can help with:\n"
        "• Answering questions\n"
        "• Writing and editing text\n"
        "• Code assistance\n"
        "• Creative tasks\n"
        "• And much more!"
    )

async def clear_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Clear conversation history for the user."""
    user_id = update.effective_user.id
    user_conversations[user_id] = model.start_chat(history=[])
    await update.message.reply_text("✅ Conversation history cleared! Starting fresh.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle incoming messages and generate AI responses."""
    user_id = update.effective_user.id
    user_message = update.message.text
    
    # Limit message length
    if len(user_message) > 4000:
        await update.message.reply_text(
            "❌ Your message is too long. Please send a shorter message (max 4000 characters)."
        )
        return
    
    # Initialize chat for new users
    if user_id not in user_conversations:
        user_conversations[user_id] = model.start_chat(history=[])
    
    try:
        # Show typing indicator
        await context.bot.send_chat_action(
            chat_id=update.effective_chat.id,
            action="typing"
        )
        
        # Get response from Gemini
        chat = user_conversations[user_id]
        
        # If history is too long, start fresh but keep context
        if len(chat.history) > 20:  # Limit to 20 messages (10 exchanges)
            logger.info(f"Clearing history for user {user_id} - too long")
            # Keep only the last 10 messages
            old_history = chat.history[-10:]
            user_conversations[user_id] = model.start_chat(history=old_history)
            chat = user_conversations[user_id]
        
        response = chat.send_message(user_message)
        
        # Send response back to user (split if too long for Telegram)
        response_text = response.text
        if len(response_text) > 4096:
            # Split long messages
            for i in range(0, len(response_text), 4096):
                await update.message.reply_text(response_text[i:i+4096])
        else:
            await update.message.reply_text(response_text)
        
    except Exception as e:
        error_message = f"Error: {type(e).__name__}: {str(e)}"
        logger.error(error_message)
        print(error_message)  # Print to console for debugging
        
        # If error is about message length, clear history and retry
        if "too long" in str(e).lower() or "BadRequest" in str(e):
            user_conversations[user_id] = model.start_chat(history=[])
            await update.message.reply_text(
                "⚠️ Conversation history was too long. I've cleared it.\n"
                "Please send your message again!"
            )
        else:
            await update.message.reply_text(
                f"❌ Sorry, I encountered an error:\n\n{error_message}\n\n"
                "Try using /clear to start a new conversation."
            )

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Log errors caused by updates."""
    logger.error(f"Update {update} caused error {context.error}")

def main():
    """Start the bot."""
    # Create the Application (disable job_queue to avoid timezone issues)
    application = (
        Application.builder()
        .token(TELEGRAM_BOT_TOKEN)
        .job_queue(None)
        .build()
    )
    
    # Register handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("clear", clear_history))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Register error handler
    application.add_error_handler(error_handler)
    
    # Start the bot
    logger.info("Bot started successfully!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()