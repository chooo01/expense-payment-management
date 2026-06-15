"""REST API — Dashboard summary (read-only, documented with APIFairy)."""
from __future__ import annotations

from apifairy import authenticate, other_responses, response
from flask import Blueprint

from api.security import token_auth
from schemas.common import ErrorSchema
from schemas.dashboard import DashboardSchema
from services.dashboard_service import DashboardService

dashboard_api = Blueprint("dashboard_api", __name__, url_prefix="/api/dashboard")
service = DashboardService()


@dashboard_api.route("", methods=["GET"])
@authenticate(token_auth)
@response(DashboardSchema)
@other_responses({401: ["Token inválido o ausente.", ErrorSchema]})
def get_dashboard():
    """Resumen ejecutivo.

    Agrega los KPIs, las series para las gráficas (Chart.js) y los saldos por
    cuenta bancaria. Es la única fuente de datos del dashboard web, por lo que
    la UI y la API comparten exactamente los mismos números.
    """
    return service.full_summary()
