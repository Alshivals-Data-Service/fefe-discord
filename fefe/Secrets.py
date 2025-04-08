import os 
class Secrets:
    """
    A class to hold sensitive credentials for accessing external services.
    """
    def __init__(self):
        # Read secrets.toml
        self.secrets_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'secrets.toml')
        self.google_oauth_client_secret = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'google_oauth_client_secret.json')
        if not os.path.exists(self.secrets_path):
            raise FileNotFoundError(f"Secrets file not found: {self.secrets_path}")
        if not os.path.exists(self.google_oauth_client_secret):
            raise FileNotFoundError(f"Google OAuth client secret file not found: {self.google_oauth_client_secret}")
        import toml
        self.secrets = toml.load(self.secrets_path)
        # Set self.key = value for each key in secrets
        for key, value in self.secrets.items():
            setattr(self, key, value)
    def get(self, key):
        """
        Get the value of a secret by key.
        """
        return getattr(self, key, None)
    def __repr__(self):
        """
        Return a string representation of the Secrets object.
        """
        return f"Secrets({self.secrets})"
secrets = Secrets()