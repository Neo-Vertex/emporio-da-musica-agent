# Catalog search with a price filter

**What it shows:** Uses `search_products` with category and max price; recommends from the results.

> The conversation is in Brazilian Portuguese, the language of the store's customers. Lines starting with 🔧 show the tools the agent called (from `python cli.py --debug`).

**Customer:** Oi! Quais opções de violões disponíveis custando até R$1000?

> 🔧 `search_products({'category': 'Violões', 'max_price': 1000})`

**Lia:** Oi! Separei as opções de violões até R$ 1.000 que estão disponíveis agora:

- Tagima Memphis AC-39 Nylon Natural — R$ 429,90
- Rozini RC-104 Nylon Estudante — R$ 459,90
- Shelby SN-100 Folk Aço Preto — R$ 549,00
- Giannini GF-1R Aço Folk Sunburst — R$ 579,90
- Yamaha C40 Nylon Natural — R$ 599,90
- Giannini GN-15 Nylon Cedr Natural — R$ 689,00
- Yamaha F310 Aço Natural — R$ 699,90
- Tagima Dallas Tuner Aço Natural — R$ 749,00
- Shelby SGD-195E Elétrico Aço Sunburst — R$ 799,00
- Yamaha C70 Nylon Natural — R$ 849,00
- Tagima Woodstock Dreadnought Natural — R$ 899,00
- Tagima TW-7 7 Cordas Aço Natural — R$ 999,00

Se quiser, eu também posso te ajudar a filtrar por nylon, aço ou por um estilo mais “estudante”/“intermediário”.

**Customer:** Sou iniciante, qual desses você indica? Prefiro corda de nylon

**Lia:** Boa! Pra iniciante e com corda de nylon, eu iria nesses 3:

- Yamaha C40 Nylon Natural — bem clássico pra estudo, timbre equilibrado e ótima pegada pra começar.
- Tagima Memphis AC-39 Nylon Natural — mais em conta e confortável, ótima opção pra entrar no violão sem gastar muito.
- Rozini RC-104 Nylon Estudante — também é bem voltado pra estudo, com um custo-benefício legal.

Se eu tivesse que te indicar um só, seria o Yamaha C40. É um modelo bem seguro pra quem tá começando. Se quiser, eu posso te mostrar qual desses sai melhor no PIX também 🙂
