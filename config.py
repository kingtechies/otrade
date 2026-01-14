import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    MT5_LOGIN = int(os.getenv("MT5_LOGIN", "0"))
    MT5_PASSWORD = os.getenv("MT5_PASSWORD", "")
    MT5_SERVER = os.getenv("MT5_SERVER", "Exness-MT5Real")
    MT5_PATH = os.getenv("MT5_PATH", "")
    
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    
    INITIAL_DEPOSIT = float(os.getenv("INITIAL_DEPOSIT", "10"))
    PRIMARY_TARGET = float(os.getenv("PRIMARY_TARGET", "10000"))
    CONTINUE_AFTER_TARGET = os.getenv("CONTINUE_AFTER_TARGET", "true").lower() == "true"
    
    SYMBOLS = os.getenv("SYMBOLS", "XAUUSD,USTECm").split(",")
    
    MAX_RISK_PER_TRADE = float(os.getenv("MAX_RISK_PER_TRADE", "0.05"))
    MAX_DAILY_TRADES = int(os.getenv("MAX_DAILY_TRADES", "100"))
    MAX_OPEN_POSITIONS = int(os.getenv("MAX_OPEN_POSITIONS", "10"))
    
    TIMEFRAMES = ["M1", "M5", "M15", "M30", "H1", "H4", "D1", "W1", "MN1"]
    PRIMARY_TIMEFRAME = os.getenv("PRIMARY_TIMEFRAME", "M15")
    
    BRAIN_DB = os.getenv("BRAIN_DB", "brain.db")
    TRADES_DB = os.getenv("TRADES_DB", "trades.db")
    
    LEARNING_RATE = float(os.getenv("LEARNING_RATE", "0.01"))
    MEMORY_SIZE = int(os.getenv("MEMORY_SIZE", "10000"))
    
    @classmethod
    def validate(cls):
        if cls.MT5_LOGIN == 0:
            raise ValueError("MT5_LOGIN required")
        if not cls.MT5_PASSWORD:
            raise ValueError("MT5_PASSWORD required")
        if not cls.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY required")
        return True


config = Config()
