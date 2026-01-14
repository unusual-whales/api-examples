"""
`protos` package

This package contains generated protobuf modules. To prevent descriptor
collisions when importing client-specific (restricted) protobufs and
full server protobufs in the same Python interpreter, we do not import
generated pb2 modules at package import time.

Import server (full) protos via:
	from protos.server import OptionState, TradeReport, OptionTrade

Import client (restricted) protos via:
	from protos.client import option_state_pb2, trade_report_pb2, options_pb2

"""

__all__ = []
