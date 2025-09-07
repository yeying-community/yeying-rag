from dataclasses import dataclass

@dataclass
class HealthResult:
    status: str          # "ok" | "error" | "disabled"
    details: str = ""    # 错误或提示信息
