# threads-jadual

Auto-post Threads mengikut jadual `posts.csv`. GitHub Actions jalan setiap 30 minit.

## Cara guna

1. Isi `posts.csv` (app Jana Video Pukal yang tulis baris ini secara automatik).
2. Setiap baris: `status=pending`, `scheduled_at` dalam format `2026-11-17T19:00+08:00`.
3. Workflow terbit post yang masa dijadualkan sudah tiba, kemudian tukar `status` kepada `done` dan isi `permalink`.

## Lajur

| Lajur | Maksud |
|---|---|
| id | ID produk atau pengenal unik |
| platform | `threads` |
| scheduled_at | masa terbit, ISO 8601 dengan offset +08:00 |
| type | `video` atau `gambar` |
| media_urls | URL media (catbox), pisah dengan `;` |
| caption | teks post utama, tanpa pautan |
| status | `pending`, `done` atau `error` |
| permalink | pautan post selepas terbit |
| error | mesej ralat jika gagal |
| topic_tag | tag topik (pilihan) |
| reply_text | reply kepada post utama, biasanya pautan produk |
| reply_media | media untuk reply (pilihan) |
| ref | rujukan dalaman (pilihan) |

## Secret (Settings > Secrets and variables > Actions)

- `THREADS_ACCESS_TOKEN`: token Threads Graph API
- `GH_PAT`: token GitHub untuk workflow menyimpan status ke repo ini
- `TELEGRAM_BOT_TOKEN` dan `TELEGRAM_CHAT_ID`: pilihan, untuk notifikasi

Jangan commit token dalam kod atau fail CSV.

## Ujian tempatan

```
pip install -r requirements.txt
THREADS_ACCESS_TOKEN=... python threads_autopost.py
```

Repo ini persendirian (private).
