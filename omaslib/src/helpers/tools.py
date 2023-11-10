
def lprint(text: str):
    lines = text.split('\n')
    for i, line in enumerate(lines, start=1):
        print(f"{i}: {line}")

