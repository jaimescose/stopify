from cryptography.fernet import Fernet


def get_encryption_key(service):
    from models import SpotifyProfile, TwitterProfile

    if service == 'twitter':
        key = TwitterProfile.get_credentials()[3]
    elif service == 'spotify':
        key = SpotifyProfile.get_credentials()[3]

    return key


def encrypt_token(value, service):
    key = get_encryption_key(service)

    value = value.encode()

    f = Fernet(key)
    value = f.encrypt(value)

    return value.decode()


def decrypt_token(value, service):
    key = get_encryption_key(service)

    value = value.encode()

    f = Fernet(key)
    value = f.decrypt(value)

    return value.decode()
