#!/usr/bin/env python3
"""
StackLabs Tell Sniper Blueprint
Mounted inside faas_server on Clio bare metal.
Exposes POST /api/snipe_tell with full Horizon Four-Layer Polymorphic dispatch.
Supports dual mounting under both FastAPI (app.include_router) and Flask (app.register_blueprint).
"""

import asyncio
import json
import os
import sys
from typing import Any, Dict

# Framework imports with dual FastAPI / Flask routing compatibility
try:
    from fastapi import APIRouter, Request
    from fastapi.responses import JSONResponse
    HAS_FASTAPI = True
except ImportError:
    HAS_FASTAPI = False
    APIRouter = object

try:
    from flask import Blueprint, jsonify, request as flask_request
    HAS_FLASK = True
except ImportError:
    HAS_FLASK = False
    flask_request = None

# Import polymorphic engine from core
sys.path.insert(0, "/home/james/stacklabs/scripts/core")
from horizon_polymorphism import (
    HardwareDispatchBridge,
    MarketOrderBookIngressVector,
    PolymorphicOutputRenderer,
    StatcastIngressVector,
    UniversalTellSniper,
)


class DualBlueprintRouter(APIRouter):
    """
    Polymorphic Router capable of mounting into FastAPI as an APIRouter
    and into Flask as a Blueprint, honoring both frameworks cleanly on dedicated local hardware.
    """

    def __init__(self, name: str = "tell_sniper", *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self.name = name

    def route(self, rule: str, **options: Any):
        methods = list(options.get("methods", ["GET"]))
        if "GET" in methods and "HEAD" not in methods:
            methods.append("HEAD")

        def decorator(f: Any):
            self.add_api_route(rule, f, methods=methods)
            if not rule.startswith("/api/"):
                alt_rule = "/api" + rule if rule.startswith("/") else "/api/" + rule
                self.add_api_route(alt_rule, f, methods=methods)
            else:
                alt_rule = rule[4:]  # strip '/api'
                self.add_api_route(alt_rule, f, methods=methods)
            return f

        return decorator

    def register(self, app: Any, options: Any):
        """Allows Flask app.register_blueprint(tell_sniper_bp) to function transparently."""
        for route in self.routes:
            endpoint_name = route.name or route.path.replace("/", "_")
            try:
                app.add_url_rule(route.path, endpoint_name, route.endpoint, methods=list(route.methods))
            except Exception:
                pass


tell_sniper_bp = DualBlueprintRouter("tell_sniper")

statcast_ingress = StatcastIngressVector()
market_ingress = MarketOrderBookIngressVector()
sniper = UniversalTellSniper()
renderer = PolymorphicOutputRenderer()
hardware_bridge = HardwareDispatchBridge()


@tell_sniper_bp.route("/api/snipe_tell", methods=["POST"])
async def snipe_tell(request: Request):
    """
    Ingests inbound human tell or machine trigger, correlates with telemetry,
    and returns a polymorphic receipt.
    """
    data: Dict[str, Any] = {}
    try:
        data = await request.json()
    except Exception:
        pass

    if not isinstance(data, dict):
        data = {}

    domain = data.get("domain", "SPORTS_STATCAST")

    if domain == "MARKET_MICROSTRUCTURE":
        payload = market_ingress.ingest(data)
    else:
        # Check if frame kinematics need Hailo-10H NPU dispatch
        if data.get("require_cv_inference"):
            cv_result = hardware_bridge.dispatch_kinematic_inference(data)
            data["head_y_displacement_norm"] = cv_result["head_y_displacement_norm"]
            data["shoulder_tilt_displacement_norm"] = cv_result["shoulder_tilt_displacement_norm"]
        payload = statcast_ingress.ingest(data)

    receipt = sniper.evaluate(payload)

    # Render polymorphic representations
    form_a = renderer.to_form_a_fanstack(receipt)
    form_b = renderer.to_form_b_institutional(receipt)
    form_c = renderer.to_form_c_iot_lighting(receipt)

    result_payload = {
        "status": receipt.status,
        "receipt_hash": receipt.receipt_hash,
        "metrics": receipt.metrics,
        "kinetics": receipt.kinetics_or_stress,
        "polymorphic_outputs": {
            "form_a_fanstack": form_a,
            "form_b_institutional": form_b,
            "form_c_iot_lighting": form_c,
        },
        # Flat compatibility fields
        "fanstack_headline": form_a.get("headline", ""),
        "robbery_verified": (receipt.status == "VERIFIED_ROBBERY"),
    }

    if HAS_FASTAPI:
        return JSONResponse(content=result_payload, status_code=200)
    elif HAS_FLASK:
        return jsonify(result_payload), 200
    return result_payload, 200


@tell_sniper_bp.route("/api/snipe_tell/health", methods=["GET", "HEAD"])
async def health():
    health_payload = {
        "service": "tell_sniper_polymorphic",
        "status": "ok",
        "engine": "Horizon 4-Layer Polymorphism",
    }
    if HAS_FASTAPI:
        return JSONResponse(content=health_payload, status_code=200)
    elif HAS_FLASK:
        return jsonify(health_payload), 200
    return health_payload, 200
