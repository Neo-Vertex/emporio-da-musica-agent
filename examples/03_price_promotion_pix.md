# Price lookup, active promotion and the PIX rule

**What it shows:** Shows original price, discount % and final price, and applies the rule that the 5% PIX discount does not stack with promotions (manual §6.2).

> The conversation is in Brazilian Portuguese, the language of the store's customers. Lines starting with 🔧 show the tools the agent called (from `python cli.py --debug`).

**Customer:** Quanto custa o Takamine GD20?

> 🔧 `search_products({'query': 'Takamine GD20'})`

**Lia:** O Takamine GD20 Dreadnought Natural sai por R$ 2.199,00.  
No PIX, sai por R$ 2.089,05.

Se quiser, eu também te passo as parcelas direitinho 😉

**Customer:** E o Crafter HT-100? Se eu pagar no PIX ganho os 5% em cima da promoção?

> 🔧 `search_products({'query': 'Crafter HT-100'})`

**Lia:** O Crafter HT-100 tá em promoção: de R$ 2.399,00 por R$ 1.967,18, 18% off.

E não, no PIX não soma mais 5% em cima da promoção. O desconto do PIX só vale em itens sem promoção.
