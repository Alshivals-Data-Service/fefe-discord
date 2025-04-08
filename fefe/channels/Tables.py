class ChatHistoryTable:
    def __init__(self):
        self.CREATE = '''
                CREATE TABLE IF NOT EXISTS chat_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    message_id INTEGER,
                    guild_id TEXT,
                    guild_name TEXT,
                    channel_id TEXT,
                    channel_name TEXT,
                    user_id TEXT,
                    user_name TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    message TEXT NOT NULL
                )'''
        self.INSERT = '''
                INSERT INTO chat_history (message_id, guild_id, guild_name, channel_id, channel_name, user_id, user_name, created_at, message)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                '''