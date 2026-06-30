"""打砖块 — thin wrapper, see vckb.apps.breakout for implementation"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from vckb.apps.breakout import main

if __name__ == '__main__':
    main()
