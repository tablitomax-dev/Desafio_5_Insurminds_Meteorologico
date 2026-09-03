"""Bootstrap de import para a suíte do pacote ai-dlc.

Garante que `contracts` e `ai_dlc_orchestrator` sejam importáveis
independente do rootdir do pytest (roda tanto da raiz quanto daqui).
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
