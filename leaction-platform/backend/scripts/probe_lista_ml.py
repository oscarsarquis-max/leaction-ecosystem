import re

from app.services.mercadolivre_public_search import _fetch_html

url = "https://lista.mercadolivre.com.br/livro-lideranca"
html = _fetch_html(url, timeout_s=15)
ids = re.findall(r"MLB\d+", html)
print("mlb ids", len(set(ids)), list(set(ids))[:5])
titles = re.findall(r'"plain_text":"([^"]{15,120})"', html)
print("plain_text", titles[:8])
poly = re.findall(r'"title".*?"text":"([^"]{15,120})"', html)
print("title text", poly[:8])
