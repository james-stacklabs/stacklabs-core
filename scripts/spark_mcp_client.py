#!/usr/bin/env python3
"""
Gemini Spark MCP Client Helper
Location: /home/james/stacklabs/scripts/spark_mcp_client.py

Provides autonomous Gemini Spark daemons and background jobs with direct
access to the Sovereign OS MCP Governance Server functions.
"""

import sys
import os

# Import MCP server tool functions directly for high-performance python calls
sys.path.insert(0, "/home/james/stacklabs")
from scripts.sovereign_mcp_server import (
    get_persona_truth,
    create_sovereign_table,
    get_sdlc_rule
)

class SparkMCPClient:
    """Client wrapper for Gemini Spark background daemons"""
    
    @staticmethod
    def fetch_persona(user_name: str) -> dict:
        """Fetch ground-truth persona data to prevent hallucinations in Spark R&D jobs"""
        return get_persona_truth(user_name)

    @staticmethod
    def create_table(table_name: str, columns_sql: str) -> str:
        """Create a table with mandatory ITSM base columns injected"""
        return create_sovereign_table(table_name, columns_sql)

    @staticmethod
    def fetch_rule(rule_key: str) -> str:
        """Fetch binding SDLC governance rule"""
        return get_sdlc_rule(rule_key)

if __name__ == "__main__":
    print("Testing Spark MCP Client connection...")
    barf_data = SparkMCPClient.fetch_persona("barf")
    print(f"Spark MCP Connected: Persona '{barf_data.get('user_name')}' -> Team: {barf_data.get('team')}")
