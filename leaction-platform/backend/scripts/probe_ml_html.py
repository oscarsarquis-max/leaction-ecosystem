import re

html = open("tmp_ofertas.html", encoding="utf-8", errors="ignore").read()
positions = [m.start() for m in re.finditer(r'"type":"ORGANIC_ITEM"', html)]
print("items", len(positions))
for pos in positions[:3]:
    chunk = html[pos : pos + 5000]
    item_id = re.search(r'"id":"(MLB\d+)"', chunk)
    url = re.search(r'"url":"(www\.mercadolivre[^"]+)"', chunk)
    pic = re.search(r'"pictures":\[\{"id":"([^"]+)"', chunk)
    title = re.search(r'"type":"title".*?"text":"((?:\\.|[^"\\])*)"', chunk, re.DOTALL)
    price = re.search(r'"value":([0-9.]+)', chunk)
    print("---")
    print("id", item_id.group(1) if item_id else None)
    print("url", url.group(1)[:60] if url else None)
    print("pic", pic.group(1) if pic else None)
    print("title", title.group(1)[:60] if title else None)
    print("price", price.group(1) if price else None)
