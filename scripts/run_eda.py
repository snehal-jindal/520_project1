"""Generate the complete EDA figures, tables and explained working report."""
from pathlib import Path
import sys
root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root))
from src.eda import run_eda
if __name__=='__main__':
    summary,_=run_eda(root)
    print(summary)
