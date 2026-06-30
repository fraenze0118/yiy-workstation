"""坦克大战 — thin wrapper, see vckb.apps.tank_battle for implementation"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from vckb.apps.tank_battle import main

if __name__ == '__main__':
    main()
