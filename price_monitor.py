"""
Monitor de preço - RTX 5060 8GB
Busca em Mercado Livre, Kabum, Terabyte, Amazon e Shopee,
compara com o histórico salvo e notifica no Telegram quando
encontra um preço novo mais baixo (ou abaixo do preço-alvo).
"""

import json
import os
import re
from datetime import datetime, timezone

import requests
from bs4 import BeautifulSoup

STATE_FILE = "state.json"
CONFIG_FILE = "config.json"

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
}


# --------------------------------------------------------------------------
# Utilidades
# --------------------------------------------------------------------------

def load_json(path, default):
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return default


def save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def send_telegram(message):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("[Telegram] Token/Chat ID não configurados. Pulando notificação.")
        print(message)
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        r = requests.post(
            url,
            data={
                "chat_id": TELEGRAM_CHAT_ID,
                "text": message,
                "parse_mode": "HTML",
                "disable_web_page_preview": False,
            },
            timeout=15,
        )
        if r.status_code != 200:
            print(f"[Telegram] Falha ao enviar: {r.status_code} {r.text}")
    except Exception as e:
        print(f"[Telegram] Erro: {e}")


def is_valid_title(title):
    """Filtra para garantir que é RTX 5060 8GB (não Ti, não 16GB, não notebook)."""
    t = title.lower()
    if "5060" not in t:
        return False
    if "8gb" not in t.replace(" ", ""):
        return False
    if " ti" in t or t.startswith("ti ") or "5060ti" in t.replace(" ", ""):
        return False
    if "notebook" in t or "laptop" in t:
        return False
    return True


def parse_price_brl(text):
    """Extrai valor tipo 'R$ 2.199,90' -> 2199.90"""
    match = re.search(r"(\d{1,3}(?:\.\d{3})*,\d{2})", text)
    if not match:
        return None
    value = match.group(1).replace(".", "").replace(",", ".")
    try:
        return float(value)
    except ValueError:
        return None


# --------------------------------------------------------------------------
# Scrapers por site
# --------------------------------------------------------------------------

def search_mercado_livre():
    results = []
    try:
        url = "https://lista.mercadolivre.com.br/rtx-5060-8gb"
        r = requests.get(url, headers=HEADERS, timeout=20)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        cards = soup.select("li.ui-search-layout__item, div.ui-search-result__wrapper")
        seen_links = set()
        for card in cards:
            link_el = card.select_one("a.ui-search-link, a.ui-search-item__group__element")
            title_el = card.select_one("h2.ui-search-item__title, h2")
            price_el = card.select_one("span.andes-money-amount__fraction")
            if not (link_el and price_el):
                continue
            link = link_el.get("href", "")
            if not link or link in seen_links:
                continue
            title = title_el.get_text(strip=True) if title_el else card.get_text(" ", strip=True)
            if not is_valid_title(title):
                continue
            price_text = price_el.get_text(strip=True)
            try:
                price = float(price_text.replace(".", "").replace(",", "."))
            except ValueError:
                continue
            results.append({"site": "Mercado Livre", "title": title, "price": price, "link": link})
            seen_links.add(link)
        print(f"[Mercado Livre] {len(results)} resultados válidos")
    except Exception as e:
        print(f"[Mercado Livre] Erro: {e}")
    return results


def search_kabum():
    results = []
    try:
        url = "https://www.kabum.com.br/busca/rtx-5060-8gb"
        r = requests.get(url, headers=HEADERS, timeout=20)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        cards = soup.select("a[href*='/produto/']")
        seen_links = set()
        for card in cards:
            link = card.get("href", "")
            if not link or link in seen_links:
                continue
            text = card.get_text(" ", strip=True)
            if not is_valid_title(text):
                continue
            price = parse_price_brl(text)
            if not price:
                continue
            if not link.startswith("http"):
                link = "https://www.kabum.com.br" + link
            results.append({"site": "Kabum", "title": text[:120], "price": price, "link": link})
            seen_links.add(link)
        print(f"[Kabum] {len(results)} resultados válidos")
    except Exception as e:
        print(f"[Kabum] Erro: {e}")
    return results


def search_terabyte():
    results = []
    try:
        url = "https://www.terabyteshop.com.br/busca?str=RTX+5060+8GB"
        r = requests.get(url, headers=HEADERS, timeout=20)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        cards = soup.select("a.list-produto, div.prod-item a, a[href*='/produto/']")
        seen_links = set()
        for card in cards:
            link = card.get("href", "")
            if not link or link in seen_links:
                continue
            text = card.get_text(" ", strip=True)
            if not is_valid_title(text):
                continue
            price = parse_price_brl(text)
            if not price:
                continue
            if not link.startswith("http"):
                link = "https://www.terabyteshop.com.br" + link
            results.append({"site": "Terabyte", "title": text[:120], "price": price, "link": link})
            seen_links.add(link)
        print(f"[Terabyte] {len(results)} resultados válidos")
    except Exception as e:
        print(f"[Terabyte] Erro: {e}")
    return results


def search_amazon():
    """Amazon bloqueia agressivamente IPs de datacenter (como o do GitHub Actions).
    Este scraper é 'best effort' e pode falhar com frequência - isso é esperado."""
    results = []
    try:
        url = "https://www.amazon.com.br/s?k=RTX+5060+8GB"
        r = requests.get(url, headers=HEADERS, timeout=20)
        if r.status_code != 200:
            print(f"[Amazon] Bloqueado ou indisponível (status {r.status_code})")
            return results
        soup = BeautifulSoup(r.text, "html.parser")
        cards = soup.select("div[data-component-type='s-search-result']")
        for card in cards:
            title_el = card.select_one("h2 span")
            price_el = card.select_one("span.a-price > span.a-offscreen")
            link_el = card.select_one("h2 a")
            if not (title_el and price_el and link_el):
                continue
            title = title_el.get_text(strip=True)
            if not is_valid_title(title):
                continue
            price = parse_price_brl(price_el.get_text(strip=True))
            if not price:
                continue
            link = "https://www.amazon.com.br" + link_el.get("href", "")
            results.append({"site": "Amazon", "title": title, "price": price, "link": link})
        print(f"[Amazon] {len(results)} resultados válidos")
    except Exception as e:
        print(f"[Amazon] Erro: {e}")
    return results


def search_shopee():
    """Shopee tem proteção anti-bot muito forte (captcha em requisições sem sessão
    de navegador real). Este endpoint é o mesmo usado pelo site, mas pode
    parar de funcionar sem aviso - é a parte mais frágil do projeto."""
    results = []
    try:
        url = "https://shopee.com.br/api/v4/search/search_items"
        params = {
            "by": "relevancy",
            "keyword": "RTX 5060 8GB",
            "limit": 30,
            "newest": 0,
            "order": "desc",
            "page_type": "search",
            "scenario": "PAGE_GLOBAL_SEARCH",
            "version": 2,
        }
        r = requests.get(url, params=params, headers=HEADERS, timeout=20)
        if r.status_code != 200:
            print(f"[Shopee] Bloqueado ou indisponível (status {r.status_code})")
            return results
        data = r.json()
        for entry in data.get("items", []):
            item = entry.get("item_basic", {})
            title = item.get("name", "")
            if not is_valid_title(title):
                continue
            price = item.get("price", 0) / 100000  # Shopee usa preço * 100000
            shopid = item.get("shopid")
            itemid = item.get("itemid")
            link = f"https://shopee.com.br/product/{shopid}/{itemid}"
            if price:
                results.append({"site": "Shopee", "title": title, "price": price, "link": link})
        print(f"[Shopee] {len(results)} resultados válidos")
    except Exception as e:
        print(f"[Shopee] Erro: {e}")
    return results


# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------

def main():
    config = load_json(CONFIG_FILE, {
        "target_price": None,
        "sites_enabled": {
            "mercado_livre": True,
            "kabum": True,
            "terabyte": True,
            "amazon": True,
            "shopee": True,
        },
    })
    sites = config.get("sites_enabled", {})

    all_results = []
    if sites.get("mercado_livre", True):
        all_results += search_mercado_livre()
    if sites.get("kabum", True):
        all_results += search_kabum()
    if sites.get("terabyte", True):
        all_results += search_terabyte()
    if sites.get("amazon", True):
        all_results += search_amazon()
    if sites.get("shopee", True):
        all_results += search_shopee()

    state = load_json(STATE_FILE, {})

    if not all_results:
        print("Nenhum resultado encontrado em nenhum site nesta execução.")
        state["last_check"] = datetime.now(timezone.utc).isoformat()
        state["last_run_found_results"] = False
        save_state(state)
        return

    all_results.sort(key=lambda x: x["price"])
    cheapest = all_results[0]

    print("\n--- Preços encontrados (ordenado) ---")
    for r in all_results:
        print(f"  R$ {r['price']:>10.2f}  |  {r['site']:<14} | {r['title'][:70]}")

    lowest_ever = state.get("lowest_price_ever")
    notify = False
    reasons = []

    if lowest_ever is None or cheapest["price"] < lowest_ever:
        notify = True
        reasons.append("novo menor preço já registrado")
        state["lowest_price_ever"] = cheapest["price"]
        state["lowest_price_site"] = cheapest["site"]
        state["lowest_price_link"] = cheapest["link"]

    target = config.get("target_price")
    if target and cheapest["price"] <= target:
        notify = True
        reasons.append(f"abaixo do seu preço-alvo (R$ {target:.2f})")

    state["last_check"] = datetime.now(timezone.utc).isoformat()
    state["last_price"] = cheapest["price"]
    state["last_run_found_results"] = True
    save_state(state)

    if notify:
        msg = (
            "🎯 <b>RTX 5060 8GB — Oportunidade!</b>\n\n"
            f"💰 <b>R$ {cheapest['price']:.2f}</b> em {cheapest['site']}\n"
            f"📦 {cheapest['title'][:100]}\n"
            f"🔗 {cheapest['link']}\n\n"
            f"Motivo: {', '.join(reasons)}"
        )
        send_telegram(msg)
        print("\nNotificação enviada.")
    else:
        print(f"\nSem novidade. Menor preço atual: R$ {cheapest['price']:.2f} ({cheapest['site']})")


if __name__ == "__main__":
    main()
