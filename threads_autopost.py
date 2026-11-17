"""Auto-post Threads mengikut jadual dalam posts.csv.

Dijalankan oleh GitHub Actions (lihat .github/workflows/autopost.yml).
Setiap baris dengan status=pending dan scheduled_at <= sekarang akan:
  1. diterbitkan sebagai post utama (caption, dengan media jika ada);
  2. jika reply_text diisi, diterbitkan sebagai reply kepada post utama tadi;
  3. dikemas kini: status=done + permalink, atau status=error + error.

Secret yang diperlukan (diset dalam GitHub Secrets, bukan dalam kod):
  THREADS_ACCESS_TOKEN   token Threads Graph API
  TELEGRAM_BOT_TOKEN     pilihan, untuk notifikasi
  TELEGRAM_CHAT_ID       pilihan, untuk notifikasi
"""
from __future__ import annotations

import csv
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import requests

GRAPH = "https://graph.threads.net/v1.0"
ZON = ZoneInfo("Asia/Kuala_Lumpur")
FAIL_CSV = Path(__file__).with_name("posts.csv")
LAJUR = ["id", "platform", "scheduled_at", "type", "media_urls", "caption", "status", "permalink",
         "error", "topic_tag", "reply_text", "reply_media", "ref"]


def tg(teks: str) -> None:
    """Hantar notifikasi Telegram jika secret diset. Gagal senyap, jangan hentikan autopost."""
    token, chat = os.environ.get("TELEGRAM_BOT_TOKEN", ""), os.environ.get("TELEGRAM_CHAT_ID", "")
    if not token or not chat:
        return
    try:
        requests.post(f"https://api.telegram.org/bot{token}/sendMessage",
                      data={"chat_id": chat, "text": teks}, timeout=20)
    except requests.RequestException:
        pass


def _post(laluan: str, data: dict) -> dict:
    token = os.environ["THREADS_ACCESS_TOKEN"]
    r = requests.post(f"{GRAPH}/{laluan}", data={**data, "access_token": token}, timeout=60)
    j = r.json()
    if r.status_code >= 400 or "error" in j:
        raise RuntimeError(j.get("error", {}).get("message") or f"HTTP {r.status_code}")
    return j


def _get(laluan: str, fields: str) -> dict:
    token = os.environ["THREADS_ACCESS_TOKEN"]
    r = requests.get(f"{GRAPH}/{laluan}", params={"fields": fields, "access_token": token}, timeout=60)
    j = r.json()
    if r.status_code >= 400 or "error" in j:
        raise RuntimeError(j.get("error", {}).get("message") or f"HTTP {r.status_code}")
    return j


def _tunggu_video(creation_id: str, had_saat: int = 300) -> None:
    """Video perlu diproses dulu. Tunggu sehingga status FINISHED."""
    tamat = time.time() + had_saat
    while time.time() < tamat:
        st = _get(creation_id, "status").get("status")
        if st == "FINISHED":
            return
        if st in ("ERROR", "EXPIRED"):
            raise RuntimeError(f"Pemprosesan video gagal: {st}")
        time.sleep(10)
    raise RuntimeError("Pemprosesan video terlalu lama")


def terbit(teks: str, media: str = "", reply_kepada: str = "") -> str:
    """Cipta container lalu terbitkan. Pulangkan ID media yang diterbitkan."""
    data = {"text": teks}
    if media:
        if media.lower().split("?")[0].endswith(".mp4"):
            data.update(media_type="VIDEO", video_url=media)
        else:
            data.update(media_type="IMAGE", image_url=media)
    else:
        data["media_type"] = "TEXT"
    if reply_kepada:
        data["reply_to_id"] = reply_kepada
    cid = _post("me/threads", data)["id"]
    if data.get("media_type") == "VIDEO":
        _tunggu_video(cid)
    return _post("me/threads_publish", {"creation_id": cid})["id"]


def permalink(media_id: str) -> str:
    try:
        return _get(media_id, "permalink").get("permalink", "")
    except RuntimeError:
        return ""


def baca() -> tuple[list[str], list[dict]]:
    with FAIL_CSV.open(newline="", encoding="utf-8") as f:
        pembaca = csv.DictReader(f)
        return list(pembaca.fieldnames or LAJUR), list(pembaca)


def tulis(lajur: list[str], baris: list[dict]) -> None:
    with FAIL_CSV.open("w", newline="", encoding="utf-8") as f:
        penulis = csv.DictWriter(f, fieldnames=lajur, extrasaction="ignore")
        penulis.writeheader()
        penulis.writerows(baris)


def sudah_tiba(masa: str, sekarang: datetime) -> bool:
    try:
        dijadual = datetime.fromisoformat(masa)
    except ValueError:
        return False
    if dijadual.tzinfo is None:
        dijadual = dijadual.replace(tzinfo=ZON)
    return dijadual <= sekarang


def jalankan() -> int:
    lajur, baris = baca()
    sekarang = datetime.now(ZON)
    diterbitkan = gagal = 0
    for b in baris:
        if b.get("status") != "pending" or not sudah_tiba(b.get("scheduled_at", ""), sekarang):
            continue
        try:
            media = (b.get("media_urls") or "").split(";")[0].strip()
            pid = terbit(b["caption"], media)
            b["permalink"] = permalink(pid)
            if (b.get("reply_text") or "").strip():
                terbit(b["reply_text"].strip(), (b.get("reply_media") or "").strip(), reply_kepada=pid)
            b["status"], b["error"] = "done", ""
            diterbitkan += 1
        except (RuntimeError, requests.RequestException, KeyError) as ralat:
            b["status"], b["error"] = "error", str(ralat)[:300]
            gagal += 1
        tulis(lajur, baris)
        tg(f"Threads {b.get('id')}: {b['status']} {b.get('error', '')}".strip())
    print(f"diterbitkan={diterbitkan} gagal={gagal}")
    return 0


if __name__ == "__main__":
    sys.exit(jalankan())
