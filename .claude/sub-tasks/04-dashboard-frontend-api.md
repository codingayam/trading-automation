# Group 04: Dashboard Frontend & API
**Priority**: User Interface - Can start after Group 02 (for data access) with mock data
**Estimated Effort**: Medium complexity, 3-4 developer-days total
**Dependencies**: Requires database schema from Group 01, market data service from Group 02

## Rationale for Grouping
The dashboard work can be split between frontend and backend API development. These can be developed in parallel using mock data initially, then integrated once the data layer is available. The dashboard is independent of the trading agent logic, only requiring read access to the database and market data.

## Tasks in This Group (Can be developed in parallel)

### Task 4.1: Dashboard Backend API
**Owner**: Backend Developer
**Effort**: 1.5 developer-days  
**Description**: Create REST API endpoints to serve dashboard data

**Acceptance Criteria**:
- Create Flask/FastAPI application with the following endpoints:
  ```
  GET /api/agents - List all agents with performance summary
  GET /api/agents/{agent_id} - Detailed agent information  
  GET /api/agents/{agent_id}/positions - Current positions for agent
  GET /api/agents/{agent_id}/performance - Performance history
  GET /api/health - System health check
  GET /api/system/status - System status and last update time
  ```
- Implement performance calculations for API responses:
  - Return (1d) % = (Current Price / Previous Close) - 1
  - Return (Since Open) % = (Current Price / Average Cost) - 1
  - Portfolio values from database with real-time price updates
- Add data caching with 15-minute refresh for market data
- Implement proper error handling and HTTP status codes
- Add request validation and parameter sanitization
- Create API response formatting with consistent JSON structure
- Add CORS configuration for frontend integration
- Implement pagination for large datasets
- Add API rate limiting to prevent abuse

**Deliverables**:
- `src/dashboard/api.py` with all required endpoints
- API response models and data serialization
- Caching layer for performance optimization
- API documentation (OpenAPI/Swagger)
- Unit tests for all API endpoints
- Error handling and validation middleware

### Task 4.2: Overview Dashboard Frontend  
**Owner**: Frontend Developer A
**Effort**: 1 developer-day
**Description**: Create the main overview dashboard showing all agents

**Acceptance Criteria**:
- Create HTML template with responsive design:
  ```
  Agent Overview Dashboard
  +--------------------------------------------------+
  | Strategy Name        | Return (1d) | Since Open |
  +--------------------------------------------------+
  | Transportation Comm. |    +2.34%   |   +15.67% |
  | Josh Gottheimer     |    -0.45%   |   +8.92%  |
  | Sheldon Whitehouse  |    +1.23%   |   +12.45% |
  | Nancy Pelosi        |    +0.89%   |   +22.10% |
  | Dan Meuser          |    -0.12%   |   +5.33%  |
  +--------------------------------------------------+
  ```
- Implement JavaScript for:
  - Auto-refresh every 60 seconds during market hours (9:30 AM - 4:00 PM EST)
  - Row click navigation to individual agent view
  - Loading states and error handling
  - Real-time update indicators
- Style with CSS for professional appearance:
  - Color coding for positive/negative returns (green/red)
  - Responsive design for desktop and tablet
  - Loading spinners and status indicators
- Add last update timestamp display
- Implement market hours detection for refresh scheduling
- Add connection status indicator

**Deliverables**:
- `src/dashboard/templates/overview.html` with complete overview layout
- `src/dashboard/static/css/dashboard.css` with styling
- `src/dashboard/static/js/overview.js` with JavaScript functionality
- Responsive design implementation
- Auto-refresh and navigation logic
- Error handling and user feedback

### Task 4.3: Individual Agent Dashboard Frontend
**Owner**: Frontend Developer B (or same as 4.2 if sequential)
**Effort**: 1 developer-day  
**Description**: Create detailed view for individual agent holdings

**Acceptance Criteria**:
- Create HTML template for individual agent view:
  ```
  [Agent Name] - Portfolio Value: $XX,XXX.XX
  +--------------------------------------------------------+
  | Ticker | Amount ($) | % of NAV | Return (1d) | Since Open |
  +--------------------------------------------------------+
  | AAPL   |   $2,500   |   15.5%  |   +1.2%    |   +8.5%   |
  | TSLA   |   $1,800   |   11.2%  |   -2.1%    |   +15.3%  |
  | MSFT   |   $3,200   |   19.8%  |   +0.8%    |   +12.1%  |
  +--------------------------------------------------------+
  ```
- Implement JavaScript for:
  - Real-time position updates with price changes
  - Sorting by different columns (amount, return, etc.)
  - Auto-refresh functionality matching overview dashboard
  - Back button navigation to overview
- Calculate and display:
  - Amount = Quantity × Current Price
  - % of NAV = Position Value / Total Portfolio Value × 100
  - Return calculations with proper formatting
- Add portfolio summary metrics:
  - Total portfolio value
  - Daily P&L and percentage change
  - Number of positions
- Style consistently with overview dashboard

**Deliverables**:
- `src/dashboard/templates/agent_detail.html` with position details
- `src/dashboard/static/js/agent_detail.js` with functionality
- Position calculation and formatting logic
- Sorting and filtering capabilities
- Navigation and back button implementation

### Task 4.4: Dashboard Data Integration & Testing
**Owner**: Full-Stack Developer (or Backend from 4.1)
**Effort**: 1 developer-day
**Description**: Integrate frontend with backend APIs and implement comprehensive testing

**Acceptance Criteria**:
- Connect frontend JavaScript to backend API endpoints
- Implement proper error handling for API failures:
  - Network connectivity issues
  - Server errors (5xx responses)
  - Data validation errors
  - Timeout handling
- Add data validation and sanitization on frontend
- Create loading states and user feedback mechanisms
- Implement proper browser caching strategies
- Add offline detection and graceful degradation
- Create end-to-end testing for complete user workflows
- Add performance monitoring for page load times
- Implement accessibility features (ARIA labels, keyboard navigation)

**Deliverables**:
- Complete API integration with error handling
- End-to-end user workflow testing
- Performance optimization and monitoring
- Accessibility compliance implementation  
- Browser compatibility testing
- User experience polish and refinement

### Task 4.5: Dashboard Deployment & Configuration
**Owner**: DevOps/Backend Developer
**Effort**: 0.5 developer-days
**Description**: Configure dashboard for production deployment

**Acceptance Criteria**:
- Create Flask/FastAPI application configuration for production
- Set up WSGI server configuration (Gunicorn/Uvicorn)
- Configure reverse proxy (Nginx) for static file serving
- Implement SSL/HTTPS configuration
- Add security headers and CSRF protection
- Configure logging for dashboard access and errors
- Set up monitoring and health checks
- Create deployment scripts and documentation
- Configure environment-specific settings

**Deliverables**:
- Production deployment configuration
- Web server configuration files
- Security and performance optimization
- Deployment automation scripts
- Production monitoring setup

## Integration Points with Other Groups
- **Group 01**: Requires database schema and configuration system
- **Group 02**: Requires market data service for price updates and calculations
- **Group 03**: Will display data from trading agents once they're operational
- **Group 05**: Dashboard will be included in integration and deployment testing

## Parallel Development Strategy
- Backend API development (Task 4.1) can start immediately after Group 02 data services
- Frontend development (Tasks 4.2 & 4.3) can start with mock data and integrate later
- Integration and testing (Task 4.4) happens after frontend/backend completion
- Deployment setup (Task 4.5) can be prepared in parallel with development

## Success Criteria
- Overview dashboard loads in < 3 seconds and displays all agents
- Individual agent dashboard shows accurate position and return data
- Auto-refresh functionality works correctly during market hours
- All calculations match requirements (1-day return, since-open return, NAV percentages)
- Navigation between views works seamlessly
- Dashboard handles API errors gracefully with user feedback
- Responsive design works on desktop and tablet devices
- Real-time price updates reflect accurately in position values
- Performance meets requirements (< 1 second API responses)

## Technical Considerations
- **Real-time Updates**: Balance between data freshness and API usage
- **Performance**: Optimize database queries and implement caching
- **Responsiveness**: Ensure dashboard works on various screen sizes
- **Error Handling**: Graceful degradation when APIs are unavailable
- **Security**: Implement proper authentication and input validation
- **Scalability**: Design for multiple concurrent dashboard users

## Mock Data Strategy (for parallel development)
- Create mock API responses matching the real API schema
- Generate realistic portfolio and performance data for testing
- Implement mock data toggle for development vs production
- Create various scenarios (gains, losses, empty portfolios)

## Risk Mitigation
- **Data Accuracy**: Validate all calculations against requirements
- **Performance**: Monitor and optimize query performance
- **Browser Compatibility**: Test across major browsers
- **API Dependencies**: Implement circuit breakers for external API calls
- **User Experience**: Conduct usability testing with realistic data

## Testing Strategy
- Unit tests for all API endpoints and calculation logic
- Frontend tests for user interactions and calculations
- Integration tests with actual database and market data
- End-to-end tests covering complete user workflows
- Performance tests under various load conditions
- Cross-browser compatibility testing