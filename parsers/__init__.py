from .mashreq import parse_mashreq
from .enbd import parse_enbd
from .emiratesislamic import parse_emiratesislamic
from .rakbank import parse_rakbank
from .generic import parse_generic
# from .adcb import parse_adcb  # add later

def get_parser(bank: str):
    bank = (bank or "").lower()
    if bank == "mashreq":
        return parse_mashreq
    elif bank == "enbd":
        return parse_enbd
    elif bank in {"emiratesislamic", "emirates islamic"}:
        return parse_emiratesislamic
    elif bank == "rakbank":
        return parse_rakbank
    # elif bank == "adcb":
    #     return parse_adcb
    else:
        return parse_generic   # fallback
