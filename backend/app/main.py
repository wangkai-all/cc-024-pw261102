"""FastAPI application.

Run from ``backend/``:

    uvicorn app.main:app --reload --port 8000

All figures are reconstructed from the DuckDB contract event stream on
startup and served from the in-process engine.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from . import config
from .db import initialize
from .engine import MrrEngine

FRONTEND_DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"


@asynccontextmanager
async def lifespan(app: FastAPI):
    conn = initialize()
    app.state.conn = conn
    app.state.engine = MrrEngine(conn)
    yield
    conn.close()


app = FastAPI(
    title="MRR 变动与首付月份留存",
    description="从合同事件还原 MRR，输出月度桥接、首付月份留存、事件流水与退款现金指标。",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def engine() -> MrrEngine:
    return app.state.engine


def resolve_month(month: str | None) -> str:
    selected = month or engine().last_completed_month
    if selected not in engine().months:
        raise HTTPException(
            status_code=400,
            detail=f"月份 {selected} 不在报告窗口内（{engine().months[0]} 至 {engine().last_completed_month}）",
        )
    return selected


@app.get("/api/health")
def health() -> dict:
    eng = engine()
    return {
        "status": "ok",
        "months": len(eng.months),
        "customers": len(eng.customers),
        "contracts": len(eng.contracts),
        "events": len(eng.events),
        "currency": config.CURRENCY,
    }


@app.get("/api/meta")
def meta() -> dict:
    return engine().meta()


@app.get("/api/mrr/bridge")
def mrr_bridge(month: str | None = Query(default=None, description="YYYY-MM，默认最近完整月份")) -> dict:
    selected = resolve_month(month)
    return engine().bridge(selected)


@app.get("/api/retention")
def retention() -> dict:
    return engine().retention_report()


@app.get("/api/retention/cell")
def retention_cell(
    cohort: str = Query(description="首付月份 YYYY-MM"),
    month: str = Query(description="观察月份 YYYY-MM"),
) -> dict:
    try:
        return engine().retention_cell(cohort, month)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"首付月份 {cohort} 没有客户")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.get("/api/customers/{customer_id}/detail")
def customer_detail(customer_id: str, month: str | None = Query(default=None)) -> dict:
    selected = resolve_month(month)
    try:
        return engine().customer_detail(customer_id, selected)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"客户 {customer_id} 不存在")


@app.get("/api/scenarios")
def scenarios() -> list[dict]:
    return engine().meta()["scenarios"]


@app.get("/api/refunds")
def refunds(month: str | None = Query(default=None)) -> dict:
    selected = resolve_month(month)
    bridge = engine().bridge(selected)
    return {
        "month": selected,
        "refund_total_rmb": bridge["refund_total_rmb"],
        "refunds": bridge["refunds"],
        "note": "退款仅计入现金指标，不修改合同 MRR。",
    }


if FRONTEND_DIST.exists():
    assets_dir = FRONTEND_DIST / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

    @app.get("/")
    def frontend_index():
        return FileResponse(FRONTEND_DIST / "index.html")

else:

    @app.get("/")
    def root_without_frontend():
        return JSONResponse(
            {
                "message": "后端已启动。前端尚未构建；开发模式请运行 `cd frontend && npm run dev`。",
                "docs": "/docs",
                "api": "/api/meta",
            }
        )
