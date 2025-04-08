import os 
class Secrets:
    """
    A class to hold sensitive credentials for accessing external services.
    """
    def __init__(
            self,
            credential_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'secrets.toml')
    ):
        # Read secrets.toml
        self.secrets_path = credential_file
        if not os.path.exists(self.secrets_path):
            raise FileNotFoundError(f"Secrets file not found: {self.secrets_path}")
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