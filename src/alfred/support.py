"""“Apoie o projeto” — Pix data and the rule for when the popup appears."""
from __future__ import annotations

import time

PIX_PAYLOAD = (
    "00020126580014BR.GOV.BCB.PIX0136596a3240-f616-4b82-b066-18bcae3ac664"
    "5204000053039865802BR5906ilgn3r6006CIDADE62070503***63046B6B"
)
PIX_RECEIVER = "ilgn3r"
POPUP_INTERVAL_DAYS = 7  # at most once a week, and only when the window is opened

TITLE = "Apoie o Alfred"
MESSAGE = (
    "O Alfred nasceu das necessidades da caverna — aquele cantinho onde @ilgn3r passa as madrugadas "
    "convertendo arquivos, editando vídeos e tentando domar o Windows. Virou o mordomo que eu queria ter: "
    "rápido, discreto e que nunca mexe no que não deve."
)
MESSAGE_2 = (
    "Enquanto muita plataforma cobra assinatura todo mês para transformar um PDF em Word, o Alfred é "
    "gratuito, sem anúncios e não manda seus arquivos para lugar nenhum. Se ele já te poupou tempo (e "
    "paciência), considere pagar um cafezinho para o mordomo: qualquer valor mantém as luzes da caverna "
    "acesas e as próximas versões chegando."
)
FOOTNOTE = "Doação voluntária. O Alfred continua 100% gratuito, com ou sem Pix."


def crc16_ccitt(data: str) -> str:
    """CRC16-CCITT (0x1021, init 0xFFFF) used by the Pix/EMV “copia e cola” payload."""
    crc = 0xFFFF
    for byte in data.encode("utf-8"):
        crc ^= byte << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021) if crc & 0x8000 else crc << 1
            crc &= 0xFFFF
    return f"{crc:04X}"


def payload_is_valid(payload: str = PIX_PAYLOAD) -> bool:
    return payload.startswith("000201") and payload[-8:-4] == "6304" and crc16_ccitt(payload[:-4]) == payload[-4:]


def should_show_popup(enabled: bool, last_shown: float, now: float | None = None) -> bool:
    now = time.time() if now is None else now
    return enabled and (now - last_shown) >= POPUP_INTERVAL_DAYS * 86400
