"""
Reusable table components for the Risk Dashboard.
"""

import logging
from typing import List, Dict, Any, Optional
from dash import html, dash_table
import dash_bootstrap_components as dbc

logger = logging.getLogger(__name__)


def DataTable(
    data: List[Dict[str, Any]],
    columns: List[Dict[str, str]],
    table_id: str,
    page_size: int = 10,
    sortable: bool = True,
    filterable: bool = True
) -> html.Div:
    """
    Create a data table with pagination and sorting.
    
    Args:
        data: Table data as list of dictionaries
        columns: Column definitions
        table_id: Unique table ID
        page_size: Number of rows per page
        sortable: Enable column sorting
        filterable: Enable column filtering
        
    Returns:
        Data table component
    """
    return html.Div([
        dash_table.DataTable(
            id=table_id,
            data=data,
            columns=columns,
            page_size=page_size,
            sort_action="native" if sortable else "none",
            filter_action="native" if filterable else "none",
            style_cell={
                'textAlign': 'left',
                'padding': '10px',
                'fontFamily': 'Arial, sans-serif'
            },
            style_header={
                'backgroundColor': 'rgb(230, 230, 230)',
                'fontWeight': 'bold'
            },
            style_data_conditional=[
                {
                    'if': {'row_index': 'odd'},
                    'backgroundColor': 'rgb(248, 248, 248)'
                }
            ]
        )
    ])


def SimpleTable(
    headers: List[str],
    rows: List[List[str]],
    striped: bool = True
) -> dbc.Table:
    """
    Create a simple Bootstrap table.
    
    Args:
        headers: Table header labels
        rows: Table row data
        striped: Enable striped rows
        
    Returns:
        Bootstrap table component
    """
    # Create header row
    header_row = html.Tr([html.Th(header) for header in headers])
    
    # Create data rows
    data_rows = []
    for row in rows:
        data_rows.append(
            html.Tr([html.Td(cell) for cell in row])
        )
    
    return dbc.Table([
        html.Thead(header_row),
        html.Tbody(data_rows)
    ], striped=striped, bordered=True, hover=True, responsive=True)
