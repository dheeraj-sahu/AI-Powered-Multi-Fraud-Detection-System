from flask import Flask, request, jsonify
import cv2
import numpy as np
import io
from PIL import Image
import pickle
import re
import pandas as pd
from transformers import pipeline
from pyzbar.pyzbar import decode
import math
from collections import Counter

app = Flask(__name__)

# Load UPI fraud detection model
with open("models/upi_model.pkl", "rb") as f:
    upi_model = pickle.load(f)

# Frequency map for vpa_domain
with open("models/vpa_domain_freq_map.pkl", "rb") as f:
    vpa_domain_map = pickle.load(f)

# Zero-shot model
text_classifier = pipeline("zero-shot-classification", model="facebook/bart-large-mnli")


def calculate_entropy(text):
    """Calculate Shannon entropy of a string"""
    if not text:
        return 0
    counter = Counter(text)
    length = len(text)
    entropy = -sum((count/length) * math.log2(count/length) for count in counter.values())
    return round(entropy, 2)

def extract_features_from_upi_url(url, vpa_domain_map):
    features = {
        "vpa_username_length": 0,
        "vpa_domain": 0,
        "vpa_contains_digits": 0,
        "amount_high_or_zero": 0,
        "is_unknown_merchant_handle": 0,
        "vpa_username_entropy": 0,
        "pn_mismatch_with_pa": 0,
        "pn_length": 0,
        "pn_entropy": 0,
        "amount_present": 0,
        "is_invalid_vpa_domain": 0
    }

    VALID_UPI_SUFFIXES = {
        "paytm", "ptm", "paytmpayments", "ybl", "ibl", "axl", "apl", "mairtel", "airtel", "freecharge", "ikwik", "fbpe",
        "oksbi", "okhdfcbank", "okicici", "okaxis", "okyesbank", "fbl", "cnrb", "upi", "mybhim", "pnb", "boi",
        "barodampay", "unionbank", "idbi", "idfc", "hdfcbank", "kmb", "ptyes", "ptys", "ptsbi"
    }

    known_domains = set(vpa_domain_map.keys()) | VALID_UPI_SUFFIXES

    # Extract VPA
    vpa_match = re.search(r"pa=([a-zA-Z0-9\.\-_@]+)", url)
    vpa = vpa_match.group(1) if vpa_match else "unknown@upi"
    username, domain = vpa.split('@')[0], vpa.split('@')[-1]

    features["vpa_username_length"] = len(username)
    features["vpa_contains_digits"] = int(any(char.isdigit() for char in username))
    features["vpa_username_entropy"] = calculate_entropy(username)
    features["vpa_domain"] = vpa_domain_map.get(domain, 0)
    features["is_invalid_vpa_domain"] = int(domain not in known_domains)
    features["is_unknown_merchant_handle"] = int(domain not in known_domains)

    # Extract amount
    amt_match = re.search(r"am=([\d\.]+)", url)
    if amt_match:
        amount = float(amt_match.group(1))
        features["amount_present"] = 1
        features["amount_high_or_zero"] = int(amount == 0 or amount > 10000)  # You can tune this threshold
    else:
        features["amount_present"] = 0
        features["amount_high_or_zero"] = 1

    # Extract payer name
    pn_match = re.search(r"pn=([a-zA-Z0-9\s]+)", url)
    pn = pn_match.group(1) if pn_match else ""
    features["pn_length"] = len(pn)
    features["pn_entropy"] = calculate_entropy(pn)

    # Name mismatch check
    features["pn_mismatch_with_pa"] = int(pn.lower() not in username.lower())

    return pd.DataFrame([features])


def process_qr_image(image_file):
    """
    Process QR code image and detect if it's a scam
    Returns a standardized result format for the template
    """
    try:
        # Open and process the image
        image = Image.open(image_file.stream).convert("RGB")
        image_array = np.array(image)
        
        # Decode QR code
        decoded_objs = decode(image_array)
        if not decoded_objs:
            return {
                "is_scam": False,
                "message": "No QR code detected in the image. Please upload a clear QR code image.",
                "type": "error"
            }

        content = decoded_objs[0].data.decode('utf-8')

        # Check if it's a UPI URL
        if "upi://" in content.lower():
            try:
                features_df = extract_features_from_upi_url(content, vpa_domain_map)
                
                # Extract VPA for display
                vpa_match = re.search(r"pa=([a-zA-Z0-9\.\-_@]+)", content)
                vpa = vpa_match.group(1) if vpa_match else "unknown@upi"

                # Get prediction from model
                prediction = upi_model.predict(features_df)[0]
                is_suspicious = prediction == 1
                
                return {
                    "is_scam": is_suspicious,
                    "message": f"UPI QR Code Analysis: {'This appears to be a suspicious/fraudulent UPI payment request' if is_suspicious else 'This appears to be a legitimate UPI payment request'} (VPA: {vpa})",
                    "type": "upi_url",
                    "vpa": vpa,
                    "prediction": "Suspicious" if is_suspicious else "Legitimate",
                    "features": features_df.to_dict(orient='records')[0]
                }
          
            except Exception as e:
                return {
                    "is_scam": True,
                    "message": f"Error analyzing UPI QR code: {str(e)}. This could indicate a malformed or suspicious QR code.",
                    "type": "error"
                }
        
        else:
            # Assume plain text → classify as Spam or Legitimate
            labels = ["Legitimate", "Spam"]
            result = text_classifier(content, candidate_labels=labels)
            return jsonify({
                "type": "text",
                "text": content,
                "classification": result["labels"][0],
                "score": result["scores"][0]
            })

    except Exception as e:
        return {
            "is_scam": True,
            "message": f"Error processing image: {str(e)}. Please ensure you're uploading a valid image file.",
            "type": "error"
        }