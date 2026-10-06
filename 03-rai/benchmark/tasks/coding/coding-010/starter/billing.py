"""Invoice computation for the hosted API product.

Grew one customer request at a time. All amounts are integer cents.
"""


def compute_invoice(customer, usage, period):
    """customer: {"id", "plan", optional "country", optional "discount_code"}
    usage: list of {"metric": "api_calls" | "storage_gb", "quantity": int}
    period: "YYYY-MM"
    """
    api_calls = 0
    storage_gb = 0
    for record in usage:
        if record["metric"] == "api_calls":
            api_calls += record["quantity"]
        elif record["metric"] == "storage_gb":
            storage_gb += record["quantity"]
        else:
            raise ValueError("unknown metric: " + str(record["metric"]))

    plan = customer["plan"]
    if plan == "free":
        if api_calls > 1000:
            raise ValueError("free plan limit exceeded")
        base = 0
        api_charge = 0
        storage_charge = max(0, storage_gb - 1) * 25
    elif plan == "starter":
        base = 900
        extra = max(0, api_calls - 10000)
        api_charge = (extra + 999) // 1000 * 40
        storage_charge = max(0, storage_gb - 10) * 20
    elif plan == "pro":
        base = 4900
        extra = max(0, api_calls - 100000)
        if extra <= 400000:
            api_charge = (extra + 999) // 1000 * 30
        else:
            api_charge = 400 * 30 + (extra - 400000 + 999) // 1000 * 20
        storage_charge = max(0, storage_gb - 100) * 15
    else:
        raise ValueError("unknown plan: " + str(plan))

    lines = [{"item": "base", "cents": base}]
    if api_charge:
        lines.append({"item": "api_calls", "cents": api_charge})
    if storage_charge:
        lines.append({"item": "storage", "cents": storage_charge})
    subtotal = base + api_charge + storage_charge

    code = customer.get("discount_code")
    discount = 0
    if code:
        code = code.strip().upper()
        if code == "WELCOME10":
            discount = round(subtotal * 0.10)
        elif code == "PRO20":
            if plan == "pro":
                discount = round(subtotal * 0.2)
        elif code.startswith("FLAT") and code[4:].isdigit():
            discount = min(subtotal, int(code[4:]) * 100)
        else:
            raise ValueError("unknown discount code: " + code)
    taxable = subtotal - discount

    country = customer.get("country", "").strip().upper()
    if country == "DE":
        rate = 0.19
    elif country == "FR" or country == "GB":
        rate = 0.20
    elif country == "NL":
        rate = 0.21
    elif country == "SA":
        rate = 0.15
    else:
        rate = 0.0
    tax = round(taxable * rate)

    return {
        "customer": customer["id"],
        "period": period,
        "lines": lines,
        "subtotal": subtotal,
        "discount": discount,
        "tax": tax,
        "total": taxable + tax,
    }
