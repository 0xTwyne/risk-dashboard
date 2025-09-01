# Twyne Risk Dashboard

A comprehensive risk monitoring dashboard for tracking EVault metrics, collateral positions, and liquidation events.

## Features

### 1. **EVaults Metrics Page**
- View all EVaults with their current metrics
- Calculate and display utilization rates (totalBorrows/totalAssets)
- Click on any vault card to view detailed historical data

### 2. **EVault Detail Page**
- Historical metrics visualization for specific vaults
- Utilization rate trends over time
- Total assets and borrows charts
- Risk assessment indicators

### 3. **Collateral Vaults Summary**
- Table view of all collateral vaults with positive assets
- Filter by liquidation status and minimum asset values
- Real-time LTV ratios and risk indicators
- Click any row to view detailed vault history

### 4. **Collateral Vault Detail Page**
- Complete historical snapshots for specific vaults
- Track position changes over time
- Monitor LTV ratio evolution
- View liquidation status history

### 5. **Liquidations Overview**
- Summary cards showing internal and external liquidation counts
- Total liquidation values in USD
- Distribution visualization
- Click cards to view detailed liquidation tables

### 6. **Liquidation Details**
- Comprehensive tables for internal/external liquidations
- Transaction details and block information
- Sortable and filterable data
- Pagination for large datasets

## Installation

### Prerequisites
- Python 3.10+
- [uv](https://github.com/astral-sh/uv) package manager

### Setup

1. Clone the repository:
```bash
git clone <repository-url>
cd risk-dashboard
```

2. Create virtual environment with uv:
```bash
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. Install dependencies:
```bash
uv pip install -r requirements.txt
```

4. Configure environment variables (optional):
```bash
cp env.example .env
# Edit .env with your API configuration
```

## Running the Dashboard

Start the dashboard server:
```bash
uv run app.py
```

The dashboard will be available at: http://0.0.0.0:8050

## Testing

Run API connectivity tests:
```bash
uv run test_api.py
```

Check dashboard status:
```bash
uv run check_dashboard.py
```

## Architecture

### Project Structure
```
risk-dashboard/
├── app.py                  # Main Dash application
├── config.py              # Configuration management
├── requirements.txt       # Dependencies
├── pages/                 # Dashboard pages
│   ├── home.py           # Home/navigation page
│   ├── evaults.py        # EVaults summary
│   ├── evault_detail.py  # EVault details
│   ├── collateral.py     # Collateral vaults summary
│   ├── collateral_detail.py # Collateral vault details
│   ├── liquidations.py   # Liquidations overview
│   └── liquidations_detail.py # Liquidation tables
├── src/
│   ├── api/              # API integration
│   │   ├── client.py     # API client with caching
│   │   ├── models.py     # Pydantic data models
│   │   └── cache.py      # Caching layer
│   ├── components/       # Reusable UI components
│   │   ├── cards.py      # Card components
│   │   ├── tables.py     # Table components
│   │   ├── charts.py     # Chart components
│   │   ├── layouts.py    # Layout templates
│   │   └── loading.py    # Loading/error states
│   ├── utils/            # Utility functions
│   │   ├── formatters.py # Data formatting
│   │   └── calculations.py # Business logic
│   └── assets/           # Static assets
│       └── style.css     # Custom styles
```

### Key Technologies
- **Dash**: Web application framework
- **Plotly**: Interactive data visualization
- **dash-bootstrap-components**: UI components
- **Pydantic**: Data validation and type safety
- **cachetools**: Response caching
- **tenacity**: Retry logic for API calls

## Configuration

### Environment Variables
- `API_BASE_URL`: API endpoint URL
- `API_KEY`: API authentication key
- `CACHE_TTL_*`: Cache durations for different data types
- `DEBUG`: Enable debug mode
- `AUTO_REFRESH_INTERVAL`: Auto-refresh interval in milliseconds

### Cache Settings
- EVaults: 30 seconds TTL
- Historical data: 5 minutes TTL
- Snapshots: 60 seconds TTL
- Liquidations: 2 minutes TTL

## Performance Features

- **Response Caching**: Reduces API calls with TTL-based caching
- **Retry Logic**: Automatic retry with exponential backoff
- **Session Pooling**: Efficient HTTP connection management
- **Lazy Loading**: Components load data on-demand
- **Pagination**: Large datasets are paginated for performance

## Known Issues

- **Internal Liquidations**: The internal liquidations API endpoint is currently broken and has been temporarily disabled in the application

## Development

### Adding New Pages
1. Create a new Python file in `pages/`
2. Register the page with `dash.register_page()`
3. Define the layout and callbacks
4. Add navigation links in the header or home page

### Custom Components
Reusable components are in `src/components/`. Follow the existing patterns for:
- Card components for metrics display
- Table components for data grids
- Chart components for visualizations
- Layout components for page structure

### API Integration
The API client in `src/api/client.py` handles:
- Authentication
- Retry logic
- Response caching
- Error handling
- Data validation with Pydantic models

## License

[Your License Here]

## Support

For issues or questions, please contact the development team or open an issue in the repository.