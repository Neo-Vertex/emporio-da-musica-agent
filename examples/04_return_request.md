# Non-trivial case: identity check + return policy

**What it shows:** Asks for the email before revealing order data (LGPD), uses `days_since_delivery` from the tool against the 7-day regret rule, declines with the reason and points to the warranty path. Note the first lookup with an empty email: the tool itself blocks it and the agent asks for the missing data.

> The conversation is in Brazilian Portuguese, the language of the store's customers. Lines starting with 🔧 show the tools the agent called (from `python cli.py --debug`).

**Customer:** Me arrependi da minha compra, posso devolver meu pedido?

**Lia:** Pode sim — se a compra foi online, você tem até 7 dias corridos após o recebimento pra pedir devolução por arrependimento.

O produto precisa estar:
- na embalagem original
- sem sinais de uso
- com manuais e acessórios

O reembolso sai na mesma forma de pagamento, em até 10 dias úteis, e o frete de devolução fica por conta da loja.

Se quiser, me passa o número do pedido que eu te oriento no próximo passo 🙂

**Customer:** É o pedido 7, comprei pelo site

> 🔧 `get_order_status({'order_id': '7', 'email_or_phone': ''})`

**Lia:** Claro — pra eu consultar certinho, me manda também o e-mail ou o telefone que foi usado na compra, por favor.

**Customer:** leticia.rocha@jmail.com

> 🔧 `get_order_status({'order_id': '7', 'email_or_phone': 'leticia.rocha@jmail.com'})`

**Lia:** Letícia, conferi aqui: seu pedido já foi entregue faz 256 dias.

Então, no caso de arrependimento, infelizmente não dá mais pra devolver por esse motivo, porque o prazo é de até 7 dias corridos após o recebimento.

Se quiser, posso te ajudar com outra dúvida do pedido ou com garantia, se for o caso.
