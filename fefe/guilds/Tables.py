import discord 
#################################################################################################################
# Guild Tables
#################################################################################################################
class GuildSettingsTable:
    def __init__(self, guild: discord.Guild):
        self.CREATE = """
                CREATE TABLE IF NOT EXISTS guild_settings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id TEXT,
                    setting_name TEXT,
                    setting_value TEXT DEFAULT NULL,
                    set_by TEXT DEFAULT 'system',
                    modified_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(guild_id, setting_name)
                );"""
        self.UPSERT = """
                INSERT INTO guild_settings (guild_id, setting_name, setting_value, set_by, modified_timestamp)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(guild_id, setting_name) DO UPDATE SET
                    setting_value = excluded.setting_value,
                    set_by = excluded.set_by,
                    modified_timestamp = CURRENT_TIMESTAMP
                """
        self.INITIATE = f"""
            INSERT INTO guild_settings (guild_id, setting_name, setting_value, set_by)
            VALUES ({guild.id}, 'model', 'gpt-4o-mini', 'system'), 
            ({guild.id}, 'app_name', 'Fefe', 'system'),
            ({guild.id}, 'personality', 'You are a kind, flirty, yet also a bit sassy and tsundere.', 'system'),
            ({guild.id}, 'language', 'en', 'system'),
            ({guild.id}, 'api_key', NULL, 'system')
            """