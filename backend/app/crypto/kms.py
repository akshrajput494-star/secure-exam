import os
from abc import ABC, abstractmethod
from typing import Any, Tuple
import boto3
from .engine import CryptoEngine, EncryptionError, DecryptionError

class KMSProvider(ABC):
    """Abstract KMS provider for key wrapping/unwrapping."""
    
    @abstractmethod
    async def generate_data_key(self) -> Tuple[bytes, bytes]:
        """Generate a new DEK. Returns (plaintext_dek, wrapped_dek)."""
        pass
    
    @abstractmethod
    async def decrypt_data_key(self, wrapped_dek: bytes) -> bytes:
        """Unwrap a DEK using the KMS master key."""
        pass

class AWSKMSProvider(KMSProvider):
    """AWS KMS integration using boto3."""
    
    def __init__(self, key_id: str):
        self.key_id = key_id
        self.client = boto3.client('kms')
        
    async def generate_data_key(self) -> Tuple[bytes, bytes]:
        try:
            response = self.client.generate_data_key(
                KeyId=self.key_id,
                KeySpec='AES_256'
            )
            return response['Plaintext'], response['CiphertextBlob']
        except Exception as e:
            raise EncryptionError(f"AWS KMS GenerateDataKey failed: {e}") from e

    async def decrypt_data_key(self, wrapped_dek: bytes) -> bytes:
        try:
            response = self.client.decrypt(
                CiphertextBlob=wrapped_dek
            )
            return response['Plaintext']
        except Exception as e:
            raise DecryptionError(f"AWS KMS Decrypt failed: {e}") from e

class LocalKMSProvider(KMSProvider):
    """Local mock KMS for development.
    
    Uses a local master key file. NOT FOR PRODUCTION.
    """
    MASTER_KEY_PATH = ".local_master_key"
    
    def __init__(self) -> None:
        if not os.path.exists(self.MASTER_KEY_PATH):
            with open(self.MASTER_KEY_PATH, "wb") as f:
                f.write(CryptoEngine.generate_dek())
                
        with open(self.MASTER_KEY_PATH, "rb") as f:
            self.master_key = f.read()
            
    async def generate_data_key(self) -> Tuple[bytes, bytes]:
        plaintext_dek = CryptoEngine.generate_dek()
        wrapped_dek = CryptoEngine.encrypt(plaintext_dek, self.master_key)
        return plaintext_dek, wrapped_dek
        
    async def decrypt_data_key(self, wrapped_dek: bytes) -> bytes:
        return CryptoEngine.decrypt(wrapped_dek, self.master_key)

def get_kms_provider(env: str, **kwargs: Any) -> KMSProvider:
    """Factory function to get the appropriate KMS provider."""
    if env.lower() == "prod":
        key_id = kwargs.get("key_id")
        if not key_id:
            raise ValueError("key_id is required for AWSKMSProvider in prod")
        return AWSKMSProvider(key_id=key_id)
    return LocalKMSProvider()
