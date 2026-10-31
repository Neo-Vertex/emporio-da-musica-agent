"""Chat with Lia in the terminal.  Usage: python cli.py [--debug]
--debug shows which tools the agent called for each answer."""
import sys

from emporio.agent import Agent

sys.stdout.reconfigure(encoding="utf-8")  # accents on the Windows terminal
debug = "--debug" in sys.argv
agent = Agent()
print("Lia (Empório da Música) — type 'exit' to quit, 'reset' to start a new conversation.\n")

while True:
    try:
        text = input("You: ").strip()
    except (EOFError, KeyboardInterrupt):
        break
    if text.lower() in {"exit", "quit", "sair"}:
        break
    if text.lower() == "reset":
        agent = Agent()
        print("(new conversation)\n")
        continue
    if not text:
        continue
    answer, tools = agent.reply(text)
    if debug:
        for t in tools:
            print(f"  [tool] {t['tool']}({t['arguments']})")
    print(f"Lia: {answer}\n")
