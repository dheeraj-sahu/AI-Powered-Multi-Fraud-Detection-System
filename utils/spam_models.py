# utils/spam_models.py

def detect_phishing(text):
    return "spam" in text.lower()

def detect_vishing(text):
    return "call" in text.lower()

def detect_identity_theft(text):
    return "ssn" in text.lower()

def detect_smishing(text):
    return "sms" in text.lower()

def detect_whaling(text):
    return "ceo" in text.lower()
