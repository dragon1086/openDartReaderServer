from fastapi import FastAPI, Query, HTTPException, Response
import OpenDartReader
import os
from urllib.parse import unquote
from datetime import date
from typing import Optional, List
from models import DartListResponse
import xml.etree.ElementTree as ET
import sys
import numpy as np
import pandas as pd

sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

app = FastAPI()

API_KEY = os.environ.get("DART_API_KEY")
if not API_KEY:
    raise ValueError("DART_API_KEY 환경 변수가 설정되지 않았습니다.")

dart = OpenDartReader(API_KEY)

@app.get("/")
def read_root():
    return {"message": "OpenDartReader API에 오신 것을 환영합니다!"}

# 1. 공시정보
# 1-1. 공시정보 - 공시검색
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

# 1-2. 공시정보 - 기업개황(기업명 기준)
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

# 1-2. 공시정보 - 기업개황(기업코드 기준)
@app.get("/companies/code/{company_code}")
def get_company(company_code: str):
    try:
        result = dart.company(company_code)
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# 1-3. 공시정보 - 공시서류원본문서 (사업보고서)
@app.get("/document/{rcp_no}")
async def get_document(
        rcp_no: str
):
    try:
        # dart.py의 document 메소드 호출
        xml_text = dart.document(rcp_no, True).replace('&', '&amp;')

        # XML 유효성 검사 (선택사항)
        try:
            ET.fromstring(xml_text)
        except ET.ParseError:
            raise HTTPException(status_code=500, detail="Invalid XML received from DART")

        # XML 응답 반환
        return Response(
            content=xml_text,
            media_type="application/xml",
            headers={
                "Content-Disposition": f"attachment; filename=document_{rcp_no}.xml"
            }
        )
    except ValueError as e:
        # dart.document 메소드에서 발생할 수 있는 ValueError 처리
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        # 기타 예외 처리
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")

# 3-4. 단일회사 전체 재무제표
@app.get("/finstates/all")
async def get_finstate_all(
        corp: str = Query(..., description="회사명 또는 종목코드"),
        bsns_year: int = Query(..., description="사업 연도"),
        reprt_code: str = Query('11011', description="보고서 코드 (기본값: 11011)"),
        fs_div: str = Query('CFS', description="재무제표 유형 (기본값: CFS)")
):
    try:
        print(f"Received corp parameter: {corp}")

        # finstate_all 메소드를 직접 호출
        data = dart.finstate_all(
            corp=corp,
            bsns_year=bsns_year,
            reprt_code=reprt_code,
            fs_div=fs_div
        )

        # 결과를 JSON 형태로 반환
        if data is None or data.empty:
            return {"message": "No data found."}
        else:
            # 무한대 값을 NaN으로 대체
            data.replace([np.inf, -np.inf], np.nan, inplace=True)
            # NaN 값을 None으로 대체
            data = data.where(pd.notnull(data), None)
            data_dict = data.to_dict(orient='records')
            return data_dict

    except ValueError as ve:
        # finstate_all 메소드에서 발생한 ValueError 처리
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        # 기타 예외 처리
        raise HTTPException(status_code=500, detail=str(e))

# 새로 추가: 배당 정보 조회 API
@app.get("/dividend/{corp}")
async def get_dividend(
    corp: str,
    year: int = Query(..., description="조회 연도"),
    quarter: str = Query('11011', description="보고서 코드 (11011:사업보고서, 11012:반기보고서, 11013:분기보고서, 11014:등록법인결산보고서)")
):
    """
    특정 기업의 배당 정보를 조회합니다.
    
    Parameters:
    - corp: 종목코드 또는 회사명
    - year: 조회 연도 (예: 2022)
    - quarter: 보고서 코드 (기본값: 11011 사업보고서)
    
    Returns:
    - 배당 관련 정보 (배당금, 배당수익률 등)
    """
    try:
        # 배당 관련 정보 조회
        result = dart.report(
            corp=corp,
            key_word='배당',
            bsns_year=year,
            reprt_code=quarter
        )
        
        if result is None or result.empty:
            return {"message": "배당 정보를 찾을 수 없습니다."}
        
        # 무한대 값과 NaN 처리
        result.replace([np.inf, -np.inf], np.nan, inplace=True)
        result = result.where(pd.notnull(result), None)
        
        # 데이터프레임을 딕셔너리로 변환하여 반환
        return {
            "corp": corp,
            "year": year,
            "quarter": quarter,
            "data": result.to_dict('records')
        }
        
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"배당 정보 조회 중 오류가 발생했습니다: {str(e)}"
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)