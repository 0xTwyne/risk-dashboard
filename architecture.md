risk-dashboard/
│
├── app.py                      # Main Dash application entry point
├── config.py                   # Configuration (API endpoints, settings)
├── requirements.txt            # Dependencies
├── .env                        # Environment variables (API keys)
├── README.md                   # Documentation
│
├── src/
│   ├── __init__.py
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   ├── client.py          # API client with error handling & caching
│   │   ├── models.py          # Pydantic models for API responses
│   │   └── cache.py           # Caching layer for API responses
│   │
│   ├── components/
│   │   ├── __init__.py
│   │   ├── cards.py           # Reusable card components
│   │   ├── tables.py          # Reusable table components
│   │   ├── charts.py          # Reusable chart components
│   │   ├── layouts.py         # Page layout templates
│   │   └── loading.py         # Loading/error state components
│   │
│   ├── pages/
│   │   ├── __init__.py
│   │   ├── home.py            # Dashboard home/navigation
│   │   ├── evaults_summary.py # EVaults metrics page (1)
│   │   ├── evault_detail.py   # Single EVault page (2)
│   │   ├── collateral_summary.py # Collateral vaults table (3)
│   │   ├── collateral_detail.py  # Single collateral vault (4)
│   │   ├── liquidations_summary.py # Liquidations cards (5)
│   │   └── liquidations_detail.py  # Liquidations table (6)
│   │
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── formatters.py      # Data formatting utilities
│   │   ├── calculations.py    # Business logic (utilization rates, etc.)
│   │   └── validators.py      # Input validation
│   │
│   └── assets/
│       ├── style.css          # Custom CSS
│       └── favicon.ico        # App icon
│
└── tests/
    ├── __init__.py
    ├── test_api.py
    ├── test_components.py
    └── test_calculations.py




KEY ARCHITECTURAL DECISIONS
Multi-Page Application Pattern
Use Dash Pages (dash.page_registry) for clean routing
Each page is a separate module with its own callbacks
URL-based navigation with parameters for detail pages
State Management Strategy
Use dcc.Store for client-side state persistence
Session storage for temporary data between pages
URL parameters for shareable links to specific views
API Integration Layer
Dedicated API client class with retry logic
Pydantic models for type safety and validation
In-memory caching with TTL for frequently accessed data
Error boundary pattern for graceful degradation
Component Architecture
Atomic design principles: atoms → molecules → organisms
Reusable components with consistent props interface
Separation of presentation and business logic
Performance Optimizations
Lazy loading for heavy components
Pagination for large datasets
Debounced callbacks for user inputs
Memoization for expensive calculations