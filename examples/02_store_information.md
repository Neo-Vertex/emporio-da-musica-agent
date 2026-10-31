# General store information

**What it shows:** Address and opening hours come straight from the manual (no tool call); installments use `simulate_installments` because the model miscalculated them during testing.

> The conversation is in Brazilian Portuguese, the language of the store's customers. Lines starting with 🔧 show the tools the agent called (from `python cli.py --debug`).

**Customer:** Qual o endereço da loja? Abre domingo?

**Lia:** Claro! A loja fica na **Rua 14 de Maio, 3200 — Centro, Campo Grande/MS, CEP 79202-333**.

E **domingo a loja fica fechada**. O horário de atendimento é:
- **Segunda a sexta:** 09:00 às 18:00
- **Sábado:** 09:00 às 13:00
- **Domingo e feriados:** fechado

Se quiser, posso te passar também o telefone/WhatsApp.

**Customer:** Dá pra parcelar uma compra de R$ 600 em quantas vezes sem juros?

> 🔧 `simulate_installments({'amount': 600})`

**Lia:** Dá sim! Em **R$ 600,00** você consegue parcelar em até **6x sem juros**, com parcela de **R$ 100,00**. 

Se quiser, posso te ajudar a ver um produto nessa faixa de preço.
