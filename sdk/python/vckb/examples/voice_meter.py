"""语音电平表 — thin wrapper, see vckb.apps.voice_meter for implementation"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from vckb.apps.voice_meter import main

if __name__ == '__main__':
    main()
