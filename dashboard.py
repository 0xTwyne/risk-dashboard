import os
import json
import datetime as dt
from typing import Dict, Any, List, Optional

import pandas as pd
import plotly.express as px
import requests
from dash import Dash, dcc, html, dash_table, callback
from dash.dependencies import Input, Output
import dash_bootstrap_components as dbc
import dash_auth
from flask_caching import Cache
from flask import Flask
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

###############################################################################
#  Configuration – Update these via environment variables on your system / in
#  your container.
###############################################################################

API_ENDPOINT: str = "https://indexer.dev.hyperindex.xyz/657ca84/v1/graphql"
# HASURA_ADMIN_SECRET: Optional[str] = os.getenv("HASURA_GRAPHQL_ADMIN_SECRET", "testing")

# Basic-auth credentials for the dashboard itself (UI access)
VALID_USERNAME_PASSWORD_PAIRS = {
    os.environ.get("DASH_USERNAME", "twyne-team"): os.environ.get("DASH_PASSWORD", "changeme-in-prod")
}

###############################################################################
#  Helper utilities
###############################################################################

def _execute_graphql_query(query: str, variables: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Send a GraphQL POST request to Hasura and return JSON data.

    Raises
    ------
    RuntimeError
        If the response contains errors or the HTTP status is not 200.
    """
    headers = {"Content-Type": "application/json"}
    # if HASURA_ADMIN_SECRET:
    #     headers["x-hasura-admin-secret"] = HASURA_ADMIN_SECRET

    payload = {
        "query": query,
        "variables": variables or {},
    }

    resp = requests.post(API_ENDPOINT, json=payload, headers=headers, timeout=15)
    if resp.status_code != 200:
        raise RuntimeError(f"Hasura responded with status {resp.status_code}: {resp.text[:200]}")

    data = resp.json()
    if "errors" in data:
        raise RuntimeError(f"GraphQL errors: {data['errors']}")
    return data["data"]


def _bigint_to_int(value: Any) -> int:
    """Convert Hasura bigint (returned as string) to Python int, safely handling None."""
    if value is None:
        return 0
    if isinstance(value, (int, float)):
        return int(value)
    return int(str(value))


def _bigint_to_float(value: Any) -> float:
    """Convert Hasura bigint to Python float, safely handling None."""
    if value is None:
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    return float(str(value))


def _scale_by_decimals(raw_amount: int, decimals: int) -> float:
    """Scale a raw token amount by its decimal places.
    
    For example: raw_amount=1000000, decimals=6 -> returns 1.0
    """
    if decimals <= 0:
        return float(raw_amount)
    return raw_amount / (10 ** decimals)


def fetch_latest_prices() -> Dict[str, float]:
    """Fetch the latest price for each aggregator from ChainlinkAggregator_AnswerUpdated.
    
    Returns
    -------
    Dict[str, float]
        Mapping from aggregator address (lowercase) to latest USD price.
    """
    query = """
    query GetLatestPrices {
        ChainlinkAggregator_AnswerUpdated(
            order_by: [{srcAddress: asc}, {blockNumber: desc}]
            distinct_on: [srcAddress]
        ) {
            srcAddress
            current
            blockNumber
            blockTimestamp
        }
    }
    """
    
    try:
        raw = _execute_graphql_query(query)["ChainlinkAggregator_AnswerUpdated"]
        
        price_map = {}
        for price_data in raw:
            aggregator_addr = price_data["srcAddress"].lower()
            # Chainlink prices are typically scaled by 8 decimals
            # Convert to actual USD price
            price_scaled = _bigint_to_float(price_data["current"]) / (10 ** 8)
            price_map[aggregator_addr] = price_scaled

        return price_map
        
    except Exception as e:
        print(f"Error fetching latest prices: {e}")
        return {}


def fetch_vault_details() -> Dict[str, Dict[str, Any]]:
    """Fetch vault details (decimals, aggregator, asset) for all known vaults.
    
    Returns
    -------
    Dict[str, Dict[str, Any]]
        Mapping from vault address (lowercase) to vault details containing
        decimals, aggregator, and asset address.
    """
    query = """
    query GetVaultDetails {
        EVaultDetails {
            id
            asset
            decimals
            aggregator
            name
            symbol
        }
        IntermediateVaultDetails {
            id
            asset
            decimals
            aggregator
            name
            symbol
        }
    }
    """
    
    try:
        raw_data = _execute_graphql_query(query)
        vault_map = {}
        
        # Process EVault details
        for vault in raw_data.get("EVaultDetails", []):
            vault_addr = vault["id"].lower()
            vault_map[vault_addr] = {
                "asset": vault["asset"].lower(),
                "decimals": _bigint_to_int(vault["decimals"]),
                "aggregator": vault["aggregator"].lower() if vault["aggregator"] else None,
                "name": vault["name"],
                "symbol": vault["symbol"]
            }
        
        # Process IntermediateVault details
        for vault in raw_data.get("IntermediateVaultDetails", []):
            vault_addr = vault["id"].lower()
            vault_map[vault_addr] = {
                "asset": vault["asset"].lower(),
                "decimals": _bigint_to_int(vault["decimals"]),
                "aggregator": vault["aggregator"].lower() if vault["aggregator"] else None,
                "name": vault["name"], 
                "symbol": vault["symbol"]
            }
            
        print(f"Fetched details for {len(vault_map)} vaults")
        return vault_map
        
    except Exception as e:
        print(f"Error fetching vault details: {e}")
        return {}


def fetch_asset_details() -> Dict[str, Dict[str, Any]]:
    """Fetch asset details (decimals, aggregator) for all known assets.
    
    Returns
    -------
    Dict[str, Dict[str, Any]]
        Mapping from asset address (lowercase) to asset details containing
        decimals and aggregator address.
    """
    # Reuse vault details but map by asset instead of vault address
    vault_details = fetch_vault_details()
    asset_map = {}
    
    for vault_addr, vault_info in vault_details.items():
        asset_addr = vault_info["asset"]
        asset_map[asset_addr] = {
            "decimals": vault_info["decimals"],
            "aggregator": vault_info["aggregator"],
            "name": vault_info["name"],
            "symbol": vault_info["symbol"]
        }
            
    print(f"Mapped details for {len(asset_map)} unique assets")
    return asset_map


def fetch_liquidation_events() -> pd.DataFrame:
    """Fetch all liquidation events from CollateralVaultFactory_T_SetCollateralVaultLiquidated.
    
    Returns
    -------
    pd.DataFrame
        DataFrame containing liquidation events sorted by blockNumber in descending order.
    """
    query = """
    query T_CollateralVaultLiquidated {
        CollateralVaultFactory_T_SetCollateralVaultLiquidated {
            id
            blockNumber
            blockTimestamp
            collateralVault
            liquidator
            srcAddress
        }
    }
    """
    
    try:
        raw = _execute_graphql_query(query)["CollateralVaultFactory_T_SetCollateralVaultLiquidated"]
        df = pd.DataFrame(raw)
        
        if df.empty:
            print("No liquidation events found")
            return df
        
        # Convert numeric columns safely
        for col in ["blockNumber", "blockTimestamp"]:
            df[col] = df[col].apply(_bigint_to_int)
        
        # Convert timestamps to human-readable format
        df["timestamp_readable"] = pd.to_datetime(df["blockTimestamp"], unit='s')
        
        # Sort by blockNumber in descending order (most recent first)
        df = df.sort_values("blockNumber", ascending=False).reset_index(drop=True)
        
        print(f"Fetched {len(df)} liquidation events")
        return df
        
    except Exception as e:
        print(f"Error fetching liquidation events: {e}")
        return pd.DataFrame()

###############################################################################
#  Data-fetching helpers
###############################################################################


def fetch_latest_collateral_vaults() -> pd.DataFrame:
    """Return latest snapshot of all EulerCollateralVaultDetails with proper scaling and USD values.
    
    Note: Each collateral vault has three different assets:
    - totalSupplied: uses the collateral vault's asset (via 'asset' field)
    - totalBorrowed: uses the target vault's asset (via 'targetVault' field) 
    - totalCredit: uses the intermediate vault's asset (via 'intermediateVault' field)
    """
    query = """
    query GetCollateralVaultDetails {
        EulerCollateralVaultDetails {
            id
            name
            symbol
            asset
            intermediateVault
            targetVault
            borrower
            twyneLiqLTV
            totalSupplied
            totalBorrowed
            totalCredit
            createdAt
        }
    }
    """
    raw = _execute_graphql_query(query)["EulerCollateralVaultDetails"]

    df = pd.DataFrame(raw)
    if df.empty:
        print("No collateral vaults found")
        return df
    
    # Convert numeric columns safely
    for col in ["totalSupplied", "totalBorrowed", "totalCredit", "createdAt", "twyneLiqLTV"]:
        df[col] = df[col].apply(_bigint_to_int)
    
    # Fetch vault details and latest prices
    vault_details = fetch_vault_details()
    latest_prices = fetch_latest_prices()
    
    # Process each vault with correct asset mappings
    for idx, row in df.iterrows():
        # Get vault addresses
        collateral_vault_asset = row["asset"].lower()
        intermediate_vault_addr = row["intermediateVault"].lower() if row["intermediateVault"] else None
        target_vault_addr = row["targetVault"].lower() if row["targetVault"] else None
        
        # Get vault details for each component
        intermediate_vault_info = vault_details.get(intermediate_vault_addr, {}) if intermediate_vault_addr else {}
        target_vault_info = vault_details.get(target_vault_addr, {}) if target_vault_addr else {}
        
        # For collateral asset, we need to find it in our vault details by asset address
        collateral_asset_info = {}
        for vault_addr, vault_info in vault_details.items():
            if vault_info.get("asset") == collateral_vault_asset:
                collateral_asset_info = vault_info
                break
        
        # Process totalSupplied (uses collateral vault's asset)
        collateral_decimals = collateral_asset_info.get("decimals", 18)
        collateral_aggregator = collateral_asset_info.get("aggregator")
        collateral_price = latest_prices.get(collateral_aggregator, 0.0) if collateral_aggregator else 0.0
        
        total_supplied_scaled = max(0, _scale_by_decimals(row["totalSupplied"], collateral_decimals))
        total_supplied_usd = total_supplied_scaled * collateral_price
        
        # Process totalBorrowed (uses target vault's asset)  
        target_decimals = target_vault_info.get("decimals", 18)
        target_aggregator = target_vault_info.get("aggregator")
        target_price = latest_prices.get(target_aggregator, 0.0) if target_aggregator else 0.0
        
        total_borrowed_scaled = max(0, _scale_by_decimals(row["totalBorrowed"], target_decimals))
        total_borrowed_usd = total_borrowed_scaled * target_price
        
        # Process totalCredit (uses intermediate vault's asset)
        intermediate_decimals = intermediate_vault_info.get("decimals", 18)
        intermediate_aggregator = intermediate_vault_info.get("aggregator")
        intermediate_price = latest_prices.get(intermediate_aggregator, 0.0) if intermediate_aggregator else 0.0
        
        total_credit_scaled = max(0, _scale_by_decimals(row["totalCredit"], intermediate_decimals))
        total_credit_usd = total_credit_scaled * intermediate_price
        
        # Process twyneLiqLTV (typically scaled by 4 decimals, representing percentage)
        twyne_liq_ltv_scaled = _scale_by_decimals(row["twyneLiqLTV"], 4)
        
        # Store all calculated values
        df.at[idx, "totalSupplied_scaled"] = total_supplied_scaled
        df.at[idx, "totalBorrowed_scaled"] = total_borrowed_scaled
        df.at[idx, "totalCredit_scaled"] = total_credit_scaled
        df.at[idx, "totalSupplied_usd"] = total_supplied_usd
        df.at[idx, "totalBorrowed_usd"] = total_borrowed_usd
        df.at[idx, "totalCredit_usd"] = total_credit_usd
        df.at[idx, "twyne_LLTV"] = twyne_liq_ltv_scaled
        
        # Store asset information for display
        df.at[idx, "collateral_symbol"] = collateral_asset_info.get("symbol", "UNK")
        df.at[idx, "target_symbol"] = target_vault_info.get("symbol", "UNK") 
        df.at[idx, "intermediate_symbol"] = intermediate_vault_info.get("symbol", "UNK")
        df.at[idx, "collateral_price"] = collateral_price
        df.at[idx, "target_price"] = target_price
        df.at[idx, "intermediate_price"] = intermediate_price
    
    # Calculate risk metrics using USD values for consistency
    df["LTV"] = df["totalBorrowed_usd"] / df["totalSupplied_usd"].replace(0, pd.NA)
    df["HF"] = (df["totalSupplied_usd"] * df["twyne_LLTV"]) / df["totalBorrowed_usd"].replace(0, pd.NA)
    
    return df


def fetch_latest_intermediate_vaults() -> pd.DataFrame:
    """Return latest snapshot of all IntermediateVaultDetails with proper scaling and USD values."""
    query = """
    query GetIntermediateVaults {
        IntermediateVaultDetails {
            id
            name
            symbol
            asset
            decimals
            aggregator
            totalSupplied
            totalBorrowed
        }
    }
    """
    raw = _execute_graphql_query(query)["IntermediateVaultDetails"]
    df = pd.DataFrame(raw)
    if df.empty:
        print("No intermediate vaults found")
        return df
    
    # Convert numeric columns safely
    for col in ["totalSupplied", "totalBorrowed", "decimals"]:
        df[col] = df[col].apply(_bigint_to_int)
    
    # Fetch latest prices
    latest_prices = fetch_latest_prices()
    
    # Add scaled and USD values
    for idx, row in df.iterrows():
        decimals = row["decimals"]
        aggregator = row["aggregator"].lower() if row["aggregator"] else None
        usd_price = latest_prices.get(aggregator, 0.0) if aggregator else 0.0
        
        # Scale amounts by decimals
        total_supplied_scaled = _scale_by_decimals(row["totalSupplied"], decimals)
        total_borrowed_scaled = _scale_by_decimals(row["totalBorrowed"], decimals)
        
        # Calculate USD values
        total_supplied_usd = total_supplied_scaled * usd_price
        total_borrowed_usd = total_borrowed_scaled * usd_price
        
        # Store scaled and USD values
        df.at[idx, "totalSupplied_scaled"] = total_supplied_scaled
        df.at[idx, "totalBorrowed_scaled"] = total_borrowed_scaled
        df.at[idx, "totalSupplied_usd"] = total_supplied_usd
        df.at[idx, "totalBorrowed_usd"] = total_borrowed_usd
        df.at[idx, "usd_price"] = usd_price
    
    # Calculate utilization based on scaled values
    df["utilization"] = df["totalBorrowed_scaled"] / df["totalSupplied_scaled"].replace(0, pd.NA)
    print(f"Fetched {len(df)} intermediate vaults")
    
    return df


###############################################################################
#  Dash application setup
###############################################################################

external_stylesheets = [dbc.themes.BOOTSTRAP]
server = Flask(__name__)
server.secret_key = os.environ.get("SECRET_KEY", "changeme-in-prod")
app = Dash(__name__, server=server, external_stylesheets=external_stylesheets)

# Attach Flask-Caching for lightweight memoisation
cache = Cache(app.server, config={"CACHE_TYPE": "filesystem", "CACHE_DIR": ".dash-cache"})
CACHE_TIMEOUT = 60  # seconds

# Basic authentication for UI access
_ = dash_auth.BasicAuth(app, VALID_USERNAME_PASSWORD_PAIRS)

###############################################################################
#  Layout helpers
###############################################################################

def make_metric_card(title: str, value: Any, color: str = "primary") -> dbc.Card:
    """Return a nicely-formatted Bootstrap card displaying a single metric."""
    return dbc.Card([
        dbc.CardBody([
            html.H6(title, className="card-title"),
            html.H4(value, className="card-text fw-bold"),
        ])
    ], color=color, inverse=True, className="text-center")

###############################################################################
#  Overall page layout
###############################################################################

app.layout = dbc.Container([
    html.H1("Twyne Protocol Dashboard", className="my-4"),

    # AUTO-REFRESH interval
    dcc.Interval(id="refresh-interval", interval=60 * 1000, n_intervals=0),

    # Metrics row – will be populated via callback
    dbc.Row(id="metrics-row", className="gy-3"),

    dbc.Tabs([
        dbc.Tab(label="Collateral Vaults", children=[
            dcc.Graph(id="collateral-risk-scatter"),
            dash_table.DataTable(
                id="collateral-table",
                style_table={"overflowX": "auto"},
                page_size=10,
                sort_action="native",
            ),
        ]),
        dbc.Tab(label="Intermediate Vaults", children=[
            dcc.Graph(id="intermediate-utilization-chart"),
            dash_table.DataTable(
                id="intermediate-table",
                style_table={"overflowX": "auto"},
                page_size=10,
                sort_action="native",
            ),
        ]),
        dbc.Tab(label="Liquidations", children=[
            html.Div(id="liquidations-summary", className="mb-3"),
            dash_table.DataTable(
                id="liquidations-table",
                style_table={"overflowX": "auto"},
                page_size=20,
                sort_action="native",
            ),
        ]),
    ]),

    html.Div(id="last-updated", className="text-end text-muted mt-2"),
], fluid=True)

###############################################################################
#  Callbacks
###############################################################################


@cache.memoize(timeout=CACHE_TIMEOUT)
def _get_cached_data() -> Dict[str, pd.DataFrame]:
    """Fetch latest data from Hasura, cached for CACHE_TIMEOUT seconds."""
    return {
        "collateral": fetch_latest_collateral_vaults(),
        "intermediate": fetch_latest_intermediate_vaults(),
        "liquidations": fetch_liquidation_events(),
    }


@callback(
    [
        Output("metrics-row", "children"),
        Output("collateral-table", "data"),
        Output("collateral-table", "columns"),
        Output("collateral-risk-scatter", "figure"),
        Output("intermediate-table", "data"),
        Output("intermediate-table", "columns"),
        Output("intermediate-utilization-chart", "figure"),
        Output("liquidations-summary", "children"),
        Output("liquidations-table", "data"),
        Output("liquidations-table", "columns"),
        Output("last-updated", "children"),
    ],
    [Input("refresh-interval", "n_intervals")],
)

def refresh_dashboard(_):
    datasets = _get_cached_data()
    cv_df: pd.DataFrame = datasets["collateral"]
    iv_df: pd.DataFrame = datasets["intermediate"]
    liq_df: pd.DataFrame = datasets["liquidations"]

    # --- Metric cards (top row) ------------------------------------------------
    total_cvs = len(cv_df)
    total_supplied_cv = cv_df["totalSupplied_usd"].sum()
    total_borrowed_cv = cv_df["totalBorrowed_usd"].sum()
    total_credit = cv_df["totalCredit_usd"].sum()
    
    # Add intermediate vault totals
    total_supplied_iv = iv_df["totalSupplied_usd"].sum() if not iv_df.empty else 0
    total_borrowed_iv = iv_df["totalBorrowed_usd"].sum() if not iv_df.empty else 0
    
    # Total protocol metrics
    total_supplied_protocol = total_supplied_cv + total_supplied_iv
    total_borrowed_protocol = total_borrowed_cv + total_borrowed_iv

    metrics = [
        make_metric_card("Collateral Vaults", f"{total_cvs}", color="primary"),
        make_metric_card("Total Supplied (USD)", f"${total_supplied_protocol:,.0f}", color="success"),
        make_metric_card("Total Borrowed (USD)", f"${total_borrowed_protocol:,.0f}", color="danger"),
        make_metric_card("Total Credit (USD)", f"${total_credit:,.0f}", color="warning"),
    ]
    metrics_row = [dbc.Col(card, width=3) for card in metrics]

    # --- Collateral Vaults table & chart --------------------------------------
    cv_df_display = cv_df.copy()
    cv_df_display["LTV"] = (cv_df_display["LTV"] * 100).round(2)
    cv_df_display["twyne_LLTV"] = (cv_df_display["twyne_LLTV"] * 100).round(2)
    cv_df_display["HF"] = cv_df_display["HF"].round(2)
    
    # Format USD values for display
    cv_df_display["totalSupplied_usd_formatted"] = cv_df_display["totalSupplied_usd"].apply(lambda x: f"${x:,.2f}")
    cv_df_display["totalBorrowed_usd_formatted"] = cv_df_display["totalBorrowed_usd"].apply(lambda x: f"${x:,.2f}")
    cv_df_display["totalCredit_usd_formatted"] = cv_df_display["totalCredit_usd"].apply(lambda x: f"${x:,.2f}")
    
    # Select and rename columns for display
    cv_df_display = cv_df_display[[
        "id", "borrower", "collateral_symbol", "target_symbol", "intermediate_symbol",
        "totalSupplied_usd_formatted", "totalBorrowed_usd_formatted", "totalCredit_usd_formatted", 
        "twyne_LLTV", "LTV", "HF"
    ]].rename(columns={
        "id": "Vault Address",
        "borrower": "Borrower Address",
        "collateral_symbol": "Collateral Asset",
        "target_symbol": "Target Asset", 
        "intermediate_symbol": "Intermediate Asset",
        "totalSupplied_usd_formatted": "Supplied (USD)",
        "totalBorrowed_usd_formatted": "Borrowed (USD)",
        "totalCredit_usd_formatted": "Credit (USD)",
        "twyne_LLTV": "Twyne LLTV (%)",
        "LTV": "LTV (%)",
        "HF": "Health Factor",
    })

    cv_columns = [{"name": c, "id": c} for c in cv_df_display.columns]
    cv_data = cv_df_display.to_dict("records")

    # Create risk scatter plot with HF color coding
    cv_scatter_df = cv_df.copy()
    # Cap HF values between 0.9 and 2.0 for better color mapping
    cv_scatter_df["HF_capped"] = cv_scatter_df["HF"].clip(lower=0.9, upper=2.0)
    
    # Filter out vaults with zero borrowed amounts for meaningful visualization
    cv_scatter_df_filtered = cv_scatter_df[cv_scatter_df["totalBorrowed_usd"] > 0].copy()
    
    if not cv_scatter_df_filtered.empty:
        cv_scatter_fig = px.scatter(
            cv_scatter_df_filtered,
            x="totalSupplied_usd",
            y="totalBorrowed_usd",
            color="HF_capped",
            size="totalCredit_usd",
            hover_data={
                "name": True,
                "borrower": True, 
                "collateral_symbol": True,
                "target_symbol": True,
                "intermediate_symbol": True,
                "LTV": ":.2%",
                "HF": ":.2f",
                "totalSupplied_usd": ":$,.2f",
                "totalBorrowed_usd": ":$,.2f", 
                "totalCredit_usd": ":$,.2f"
            },
            title="Collateral Vault Risk Analysis: Supplied vs Borrowed (Color = Health Factor)",
            labels={
                "totalSupplied_usd": "Total Supplied (USD)",
                "totalBorrowed_usd": "Total Borrowed (USD)",
                "HF_capped": "Health Factor",
                "totalCredit_usd": "Credit Size (USD)"
            },
            color_continuous_scale="RdYlBu",  # Red-Yellow-Blue scale (red=low, blue=high)
            range_color=[0.9, 2.0],
        )
        
        # Update layout for better readability
        cv_scatter_fig.update_layout(
            xaxis_title="Total Supplied (USD)",
            yaxis_title="Total Borrowed (USD)",
            coloraxis_colorbar_title="Health Factor<br>(Capped 0.9-2.0)",
        )
    else:
        # Create empty plot if no data
        cv_scatter_fig = px.scatter(
            title="Collateral Vault Risk Analysis: No Data Available"
        )

    # --- Intermediate Vaults table & chart ------------------------------------
    iv_df_display = iv_df.copy()
    iv_df_display["utilization"] = (iv_df_display["utilization"] * 100).round(2)
    
    # Format USD values for display
    iv_df_display["totalSupplied_usd_formatted"] = iv_df_display["totalSupplied_usd"].apply(lambda x: f"${x:,.2f}")
    iv_df_display["totalBorrowed_usd_formatted"] = iv_df_display["totalBorrowed_usd"].apply(lambda x: f"${x:,.2f}")
    iv_df_display["usd_price_formatted"] = iv_df_display["usd_price"].apply(lambda x: f"${x:,.4f}")
    
    # Select and rename columns for display
    iv_df_display = iv_df_display[[
        "id", "symbol", "totalSupplied_usd_formatted", "totalBorrowed_usd_formatted",
        "utilization"
    ]].rename(columns={
        "id": "Vault Address",
        "symbol": "Vault Symbol",
        "totalSupplied_usd_formatted": "Total Supplied (USD)",
        "totalBorrowed_usd_formatted": "Total Borrowed (USD)",
        "utilization": "Utilization (%)",
    })

    iv_columns = [{"name": c, "id": c} for c in iv_df_display.columns]
    iv_data = iv_df_display.to_dict("records")

    # Use the unformatted data for charting
    iv_chart_df = iv_df.copy()
    iv_fig = px.bar(
        iv_chart_df,
        x="name",
        y=["totalSupplied_usd", "totalBorrowed_usd"],
        barmode="group",
        title="Intermediate Vault – USD Assets vs Borrowed",
        labels={"value": "USD Amount", "variable": "Metric", "name": "Vault Name"},
    )

    # --- Liquidations table & summary ------------------------------------------
    total_liquidations = len(liq_df)
    
    # Create liquidations summary
    liquidations_summary = dbc.Alert([
        html.H5(f"Total Liquidation Events: {total_liquidations}", className="mb-0")
    ], color="warning", className="text-center")
    
    # Prepare liquidations table
    if not liq_df.empty:
        liq_df_display = liq_df.copy()
        
        # Format the data for display
        liq_df_display = liq_df_display[[
            "id", "blockNumber", "timestamp_readable", "collateralVault", 
            "liquidator", "srcAddress"
        ]].rename(columns={
            "id": "Event ID",
            "blockNumber": "Block Number",
            "timestamp_readable": "Timestamp",
            "collateralVault": "Collateral Vault",
            "liquidator": "Liquidator",
            "srcAddress": "Source Address"
        })
        
        # Convert timestamp to string for better display
        liq_df_display["Timestamp"] = liq_df_display["Timestamp"].dt.strftime('%Y-%m-%d %H:%M:%S UTC')
        
        liq_columns = [{"name": c, "id": c} for c in liq_df_display.columns]
        liq_data = liq_df_display.to_dict("records")
    else:
        liq_columns = []
        liq_data = []

    # --------------------------------------------------------------------------
    last_updated_text = f"Last updated: {dt.datetime.now(dt.UTC).strftime('%Y-%m-%d %H:%M:%S')} UTC"

    return (
        metrics_row,
        cv_data,
        cv_columns,
        cv_scatter_fig,
        iv_data,
        iv_columns,
        iv_fig,
        liquidations_summary,
        liq_data,
        liq_columns,
        last_updated_text,
    )


###############################################################################
#  Main entry point – this file can be run standalone (python dashboard_graphql.py)
###############################################################################

if __name__ == "__main__":
    # Expose on 0.0.0.0 so that containerised deployments work by default.
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8050)), debug=False)