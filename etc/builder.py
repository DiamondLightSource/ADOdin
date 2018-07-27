import os
import sys

# Import detector specific objects from other modules to expose them to builder
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import excalibur
import eiger
