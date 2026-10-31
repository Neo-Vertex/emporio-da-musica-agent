"""Conversa com a Lia no terminal.  Uso: python cli.py [--debug]
--debug mostra quais ferramentas o agente chamou em cada resposta."""
import sys

from emporio.agent import Agent

sys.stdout.reconfigure(encoding="utf-8")  # acentos no terminal do Windows
debug = "--debug" in sys.argv
agent = Agent()
print("Lia (Empório da Música) — digite 'sair' para encerrar, 'reset' para nova conversa.\n")

while True:
    try:
        text = input("Você: ").strip()
    except (EOFError, KeyboardInterrupt):
        break
    if text.lower() in {"sair", "exit", "quit"}:
        break
    if text.lower() == "reset":
        agent = Agent()
        print("(nova conversa)\n")
        continue
    if not text:
        continue
    answer, tools = agent.reply(text)
    if debug:
        for t in tools:
            print(f"  [ferramenta] {t['ferramenta']}({t['argumentos']})")
    print(f"Lia: {answer}\n")
