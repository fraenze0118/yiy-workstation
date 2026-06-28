"""番茄钟 — thin wrapper, see vckb.apps.tomato for implementation"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from vckb.apps.tomato import main

if __name__ == '__main__':
    main()
