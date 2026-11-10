from pathlib import Path
print(Path(__file__).with_name('state.json').read_text())
