"""屏幕镜像 — thin wrapper, see vckb.apps.screen_mirror for implementation"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from vckb.apps.screen_mirror import main

if __name__ == '__main__':
    main()
