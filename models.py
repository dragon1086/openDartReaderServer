from pydantic import BaseModel
from datetime import date
from typing import Optional

class DartListResponse(BaseModel):
    corp_cls: str
    corp_code: str
    corp_name: str
    flr_nm: str
    rcept_dt: str
    rcept_no: str
    report_nm: str
    rm: str
    stock_code: Optional[str]