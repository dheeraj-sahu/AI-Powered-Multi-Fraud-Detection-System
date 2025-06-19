def detect_fraud(tx, user, device_id, known_devices, ip_loc, prev_loc):
    alerts = []
    if tx['amount'] > user['payment_limit']:
        alerts.append("Exceeds limit")
    if tx['amount'] > 3 * user['avg_amount']:
        alerts.append("High value tx")
    if tx['beneficiary_account'] not in user['beneficiaries']:
        if tx['amount'] > 1000:
            alerts.append("New + high beneficiary")
    if device_id not in known_devices:
        alerts.append("New device")
    if ip_loc != prev_loc:
        alerts.append("IP mismatch")
    return {"status": "Flagged" if alerts else "Safe", "reason": "; ".join(alerts)}