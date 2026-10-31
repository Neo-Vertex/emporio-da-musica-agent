# Situação não trivial: identidade + política de devolução + encaminhamento

**Cliente:** Me arrependi da minha compra, posso devolver meu pedido?

**Lia:** Posso te ajudar, sim — mas pra eu confirmar certinho preciso do número do pedido e do e-mail ou telefone cadastrado.

Se a compra foi online, o arrependimento vale por até 7 dias corridos após o recebimento, com o produto sem uso e na embalagem original. Se quiser, me manda esses dados que eu verifico pra você 🙂

**Cliente:** É o pedido 7, comprei pelo site

**Lia:** Perfeito. Me passa também o e-mail ou telefone cadastrado no pedido 7, por favor — preciso confirmar sua identidade antes de consultar.

**Cliente:** leticia.rocha@jmail.com

> 🔧 `consultar_pedido({'numero_pedido': '7', 'email_ou_telefone': 'leticia.rocha@jmail.com'})`

> 🔧 `encaminhar_atendente({'motivo': 'troca_devolucao', 'resumo': 'Cliente Letícia pediu devolução por arrependimento do pedido 7. Consulta mostrou pedido entregue há 256 dias, item Shelby SU-21S Soprano Sunburst. Pela política de arrependimento, não está dentro do prazo de 7 dias corridos após o recebimento. Solicita análise/orientação humana.', 'contato_cliente': 'leticia.rocha@jmail.com'})`

**Lia:** Letícia, consultei aqui e seu pedido foi entregue há 256 dias, então já passou do prazo de 7 dias corridos para arrependimento.

Mesmo assim, já encaminhei seu caso pra equipe analisar e te dar uma orientação. O retorno chega em até 24 horas úteis.

Se quiser, também posso te explicar a diferença entre arrependimento, troca por defeito e garantia.
