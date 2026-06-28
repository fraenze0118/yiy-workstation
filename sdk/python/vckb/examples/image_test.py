"""位图传输测试 — thin wrapper, see vckb.apps.image_test for implementation"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from vckb.apps.image_test import main

if __name__ == '__main__':
    main()
