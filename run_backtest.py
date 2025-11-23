import sys
import os

# Ensure the current directory is in the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.engine import main

if __name__ == "__main__":
    main()
