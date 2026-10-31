"""Ferramentas que o agente pode chamar. Toda conta (promoção, PIX, parcelas) é feita aqui,
em código, para o modelo nunca precisar calcular nem inventar preço."""
import csv
import json
import re
import unicodedata
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

# Campo Grande/MS = UTC-4 o ano todo (sem horário de verão desde 2019); evita depender de tzdata no Windows
TZ = timezone(timedelta(hours=-4))


def today():
    return datetime.now(TZ).date()

DATA = Path(__file__).resolve().parent.parent / "data"
LOGS = Path(__file__).resolve().parent.parent / "logs"


def _load(name):
    with open(DATA / f"desafio_tecnico_ai_eng - {name}.csv", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _norm(text):
    """minúsculas, sem acento, sem espaço/hífen: 'Violão GD-20' -> 'violaogd20'."""
    text = unicodedata.normalize("NFKD", str(text)).encode("ascii", "ignore").decode()
    return re.sub(r"[\s\-_/'.]", "", text.lower())


CATEGORIES = {c["category_id"]: c["name"] for c in _load("categories")}
PRODUCTS = _load("products")
CUSTOMERS = {c["customer_id"]: c for c in _load("customers")}
ORDERS = {o["order_id"]: o for o in _load("orders")}
ORDER_ITEMS = _load("order_items")
ACTIVE_PROMOS = {p["product_id"]: p for p in _load("promotions") if p["is_active"] == "1"}
PRODUCT_BY_ID = {p["product_id"]: p for p in PRODUCTS}

AVAILABILITY = {"discontinued": "descontinuado", "coming_soon": "em breve (pré-lançamento)"}
STATUS_PT = {
    "pending": "aguardando pagamento/confirmação",
    "confirmed": "pagamento confirmado, em separação",
    "shipped": "enviado",
    "delivered": "entregue",
    "cancelled": "cancelado",
}


def max_installments(price):
    """Maior nº de parcelas sem juros (manual §3.1): até 3x com parcela >= R$50,
    4-6x com parcela >= R$80, 7-12x com parcela >= R$100."""
    for n in range(12, 0, -1):
        minimum = 100 if n >= 7 else 80 if n >= 4 else 50
        if price / n >= minimum:
            return n
    return 1


def _availability(p):
    if p["status"] in AVAILABILITY:
        return AVAILABILITY[p["status"]]
    stock = int(p["stock_quantity"])
    return f"em estoque ({stock} un.)" if stock > 0 else "esgotado"


def _product_view(p):
    price = float(p["price_brl"])
    view = {
        "id": int(p["product_id"]),
        "nome": p["name"],
        "categoria": CATEGORIES.get(p["category_id"]),
        "disponibilidade": _availability(p),
        "preco_tabela": round(price, 2),
        "descricao": p["description"],
        "especificacoes": json.loads(p["specs"] or "{}"),
    }
    promo = ACTIVE_PROMOS.get(p["product_id"])
    if promo:
        final = round(price * (1 - int(promo["discount_percent"]) / 100), 2)
        view["promocao_ativa"] = {"nome": promo["description"], "desconto_percent": int(promo["discount_percent"]),
                                  "preco_promocional": final}
        view["preco_pix"] = final  # §6.2: desconto PIX não acumula com promoção
    else:
        final = price
        view["preco_pix"] = round(price * 0.95, 2)
    view["parcelamento_max_sem_juros"] = f"{max_installments(final)}x de R$ {final / max_installments(final):.2f}"
    return view


def buscar_produtos(termo=None, categoria=None, preco_min=None, preco_max=None, somente_promocao=False):
    cat_ids = {cid for cid, name in CATEGORIES.items() if categoria and _norm(categoria) in _norm(name)}
    words = [_norm(w) for w in (termo or "").split() if w.strip()]
    found = []
    for p in PRODUCTS:
        price = float(p["price_brl"])
        haystack = _norm(p["name"] + p["description"] + CATEGORIES.get(p["category_id"], ""))
        if categoria and p["category_id"] not in cat_ids:
            continue
        if any(w not in haystack for w in words):
            continue
        if (preco_min is not None and price < preco_min) or (preco_max is not None and price > preco_max):
            continue
        if somente_promocao and p["product_id"] not in ACTIVE_PROMOS:
            continue
        found.append(p)
    # disponíveis primeiro, depois por preço
    found.sort(key=lambda p: (not _availability(p).startswith("em estoque"), float(p["price_brl"])))
    return {"total_encontrado": len(found), "produtos": [_product_view(p) for p in found[:20]]}


def consultar_pedido(numero_pedido, email_ou_telefone):
    order = ORDERS.get(str(numero_pedido).strip().lstrip("#"))
    if not order:
        return {"erro": "Pedido não encontrado."}
    customer = CUSTOMERS[order["customer_id"]]
    given = _norm(email_ou_telefone)
    digits = re.sub(r"\D", "", email_ou_telefone)
    phone_ok = len(digits) >= 8 and re.sub(r"\D", "", customer["phone"]).endswith(digits[-8:])
    if given != _norm(customer["email"]) and not phone_ok:
        # LGPD: não revela nada (nem se o pedido existe para outra pessoa)
        return {"erro": "Não foi possível confirmar a identidade. E-mail ou telefone não confere com o pedido."}
    items = [{"produto": PRODUCT_BY_ID[i["product_id"]]["name"], "quantidade": int(i["quantity"])}
             for i in ORDER_ITEMS if i["order_id"] == order["order_id"]]
    extra = {}
    if order["estimated_delivery"]:
        days = (today() - date.fromisoformat(order["estimated_delivery"])).days
        if order["status"] == "delivered":
            # não há data real de entrega nos dados: usamos a previsão como data de recebimento
            extra["dias_desde_entrega"] = days
        elif days > 0:
            extra["dias_de_atraso"] = days
    return extra | {
        "pedido": int(order["order_id"]),
        "cliente_primeiro_nome": customer["name"].split()[0],
        "data_pedido": order["order_date"],
        "status": STATUS_PT.get(order["status"], order["status"]),
        "itens": items,
        "total": float(order["total_brl"]),
        "pagamento": order["payment_method"],
        "codigo_rastreio": order["tracking_code"] or None,
        "previsao_entrega": order["estimated_delivery"] or None,
        "observacao": order["notes"] or None,
    }


def encaminhar_atendente(motivo, resumo, contato_cliente=None):
    # ponytail: arquivo JSONL faz o papel de fila; em produção seria um ticket no CRM/helpdesk
    LOGS.mkdir(exist_ok=True)
    ticket = {"quando": datetime.now(TZ).isoformat(timespec="seconds"), "motivo": motivo,
              "resumo": resumo, "contato": contato_cliente}
    with open(LOGS / "encaminhamentos.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(ticket, ensure_ascii=False) + "\n")
    return {"ok": True, "prazo_retorno": "até 24 horas úteis"}


TOOLS = {f.__name__: f for f in (buscar_produtos, consultar_pedido, encaminhar_atendente)}

SCHEMAS = [
    {"type": "function", "function": {
        "name": "buscar_produtos",
        "description": "Busca no catálogo da loja. Use para QUALQUER pergunta sobre produto, preço, estoque, "
                       "promoção ou recomendação. Retorna preço de tabela, promoção ativa, preço no PIX e parcelamento já calculados.",
        "parameters": {"type": "object", "properties": {
            "termo": {"type": "string", "description": "Marca, modelo ou característica (ex.: 'Takamine GD20', 'nylon', 'elétrico'). Omitir para listar a categoria."},
            "categoria": {"type": "string", "enum": sorted(CATEGORIES.values())},
            "preco_min": {"type": "number"},
            "preco_max": {"type": "number"},
            "somente_promocao": {"type": "boolean", "description": "true para listar só itens com promoção ativa"},
        }}}},
    {"type": "function", "function": {
        "name": "consultar_pedido",
        "description": "Consulta status, itens e rastreio de um pedido. Exige o número do pedido E o e-mail ou telefone "
                       "do cliente para confirmar identidade (LGPD). Peça ao cliente se faltar algum dos dois.",
        "parameters": {"type": "object", "required": ["numero_pedido", "email_ou_telefone"], "properties": {
            "numero_pedido": {"type": "string"},
            "email_ou_telefone": {"type": "string"},
        }}}},
    {"type": "function", "function": {
        "name": "encaminhar_atendente",
        "description": "Encaminha o caso para a equipe humana: reclamação, pedido de devolução/troca a formalizar, "
                       "pedido atrasado, frete especial ou qualquer coisa que o agente não consiga resolver.",
        "parameters": {"type": "object", "required": ["motivo", "resumo"], "properties": {
            "motivo": {"type": "string", "enum": ["reclamacao", "troca_devolucao", "atraso_entrega", "cotacao_frete", "outro"]},
            "resumo": {"type": "string", "description": "Resumo do caso para o atendente, com nº do pedido se houver."},
            "contato_cliente": {"type": "string"},
        }}}},
]


if __name__ == "__main__":  # auto-checagem: python -m emporio.tools
    assert max_installments(2199) == 12 and max_installments(400) == 5 and max_installments(120) == 2
    gd20 = buscar_produtos("takamine gd20")["produtos"][0]
    assert gd20["preco_tabela"] == 2199 and "promocao_ativa" not in gd20 and gd20["preco_pix"] == 2089.05
    crafter = buscar_produtos("crafter ht-100")["produtos"][0]  # promo ativa 18%: PIX não acumula
    assert crafter["promocao_ativa"]["preco_promocional"] == crafter["preco_pix"] == 1967.18
    violoes = buscar_produtos(categoria="Violões", preco_max=1000)["produtos"]
    assert violoes and all(v["preco_tabela"] <= 1000 for v in violoes)
    assert "erro" in consultar_pedido("8", "outra@pessoa.com")
    assert consultar_pedido("8", "anacarol.ferreira@coldmail.com")["status"] == "enviado"
    assert consultar_pedido("8", "(67) 99654-7821")["codigo_rastreio"] == "BRJL5544332BR"
    print("ok")
