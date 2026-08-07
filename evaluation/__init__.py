"""
NyayaSetu Evaluation Framework
==============================

A standalone evaluation subsystem for NyayaSetu, decoupled from the
application runtime. It treats the backend API and the Colab notebook as
black boxes (HTTP), the same way a production monitoring system or an
external reviewer would, so evaluation results are not invalidated by
internal refactors on either side.

See evaluation/README.md for the full design and usage guide.
"""

__version__ = "0.1.0"
