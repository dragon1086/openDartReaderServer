from fastapi import FastAPI, Query, HTTPException
import OpenDartReader
import os
from urllib.parse import unquote
from datetime import date
from typing import Optional, List
from models import DartListResponse

app = FastAPI()

API_KEY = os.environ.get("DART_API_KEY")
if not API_KEY:
    raise ValueError("DART_API_KEY 환경 변수가 설정되지 않았습니다.")

dart = OpenDartReader(API_KEY)

@app.get("/")
def read_root():
    return {"message": "OpenDartReader API에 오신 것을 환영합니다!"}

@app.get("/companies/name/{name}")
async def get_company_by_name(name: str):
    try:
        # URL 디코딩
        decoded_name = unquote(name)
        result = dart.company_by_name(decoded_name)

        # 결과가 리스트인 경우 (비어 있지 않으면) 그대로 반환
        if result:
            return result
        else:
            return {"message": f"No companies found with name containing '{decoded_name}'"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/companies/code/{company_code}")
def get_company(company_code: str):
    try:
        result = dart.company(company_code)
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/list", response_model=List[DartListResponse])
async def get_dart_list(
        corp: Optional[str] = None,
        start: Optional[date] = None,
        end: Optional[date] = None,
        kind: Optional[str] = Query(None, max_length=1),
        kind_detail: Optional[str] = None,
        final: bool = True
):
    try:
        result = dart.list(
            corp=corp,
            start=start.isoformat() if start else None,
            end=end.isoformat() if end else None,
            kind=kind,
            kind_detail=kind_detail,
            final=final
        )
        return result.to_dict('records')
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)