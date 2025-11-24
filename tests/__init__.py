from pathlib import Path
import sys

# Ensure source package is importable when tests run without installation
sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))
