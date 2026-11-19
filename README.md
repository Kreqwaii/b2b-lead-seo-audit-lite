# B2B Lead & SEO Audit CLI (Lite) — Website Email Extractor & Technical SEO Checker

Zero-dependency **Python 3.9+ stdlib** CLI tool for web agencies, SEO specialists, and B2B marketers.  
Inspect any single URL for HTTP status, response latency, HTTPS, `<title>`, `<meta name="description">`, `<meta name="viewport">`, footer copyright year, and valid business email addresses (filtering out `.png`, `.svg`, `example.com`, and asset false positives).

---

## Features (Lite)

- **100% Python 3.9+ stdlib** — no `pip install`, no virtualenvs, no external packages
- **Technical SEO snapshot**: HTTP status code, response time (ms), HTTPS check, `<title>`, `<meta name="description">`, `<meta name="viewport">`
- **Outdated site signal**: extracts the latest copyright year from the page/footer
- **Clean email extraction**: parses `mailto:` links and page HTML while filtering out image/asset filenames (`.png`, `.svg`, etc.) and placeholder domains (`example.com`)
- **JSON or Table output** for quick terminal checks or piping into other scripts
- **Built-in `--self-test`** using a local `ThreadingHTTPServer`

---

## Quick Start

```bash
# Audit a single website (table output)
python audit_url.py https://example.org

# Output clean JSON
python audit_url.py https://example.org --format json

# Run built-in self-test
python audit_url.py --self-test
```

---

## Lite vs Pro Comparison

| Feature | Lite Single-URL CLI (Free MIT) | Pro Multi-Threaded Batch Lead Extractor |
|---|---|---|
| Python 3.9+ stdlib (0 dependencies) | Yes | Yes |
| Single-URL SEO & Email check | Yes | Yes |
| Multi-threaded batch processing (CSV/TXT lists) | No | **Yes** |
| `/contact` & `/about` auto-crawl | No | **Yes** |
| Phones + Telegram / WhatsApp / Socials extraction | No | **Yes** |
| CMS detector (WordPress, Shopify, Wix, etc.) | No | **Yes** |
| 0–100 Opportunity Score for B2B outreach | No | **Yes** |
| Excel-ready UTF-8-SIG CSV Export | No | **Yes** |

**Need batch enrichment for agencies & lead gen?**  
Get the **Pro Multi-Threaded Batch Lead Extractor** here: [https://funpay.com/lots/offer?id=82599378](https://funpay.com/lots/offer?id=82599378)

---

## Краткое описание (RU)

Бесплатная CLI-утилита на чистом **Python 3.9+ stdlib** (без сторонних библиотек) для быстрого SEO-аудита и извлечения рабочих email-адресов с одного URL:
- Проверяет HTTP-статус, время ответа (мс), HTTPS, `<title>`, `<meta name="description">`, `<meta name="viewport">` и год копирайта в футере.
- Извлекает валидные email-адреса с отсевом мусора (`.png`, `.svg`, `example.com`).
- Для массового парсинга списков доменов (CSV/TXT), авто-обхода `/contact`, сбора телефонов/Telegram/WhatsApp/соцсетей, детектора CMS, скоринга 0–100 и экспорта в Excel UTF-8-SIG CSV доступна **Pro-версия**: [https://funpay.com/lots/offer?id=82599378](https://funpay.com/lots/offer?id=82599378)

---

## License

MIT License — see [LICENSE](LICENSE).
