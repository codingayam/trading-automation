/**
 * Agent Detail Dashboard JavaScript
 * Handles individual agent dashboard functionality including position data,
 * performance metrics, auto-refresh, and navigation.
 */

class AgentDetailDashboard {
    constructor() {
        this.agentId = null;
        this.agentName = null;
        this.refreshInterval = null;
        this.refreshRate = 60000; // 60 seconds
        this.connectionTimeout = 10000; // 10 seconds
        this.retryCount = 0;
        this.maxRetries = 3;
        this.sortColumn = 'market_value';
        this.sortDirection = 'desc';
        
        this.init();
    }

    init() {
        console.log('Initializing Agent Detail Dashboard...');
        
        // Get agent data from DOM
        this.loadAgentConfig();
        
        if (!this.agentId) {
            console.error('No agent ID found');
            return;
        }
        
        // Load initial data
        this.loadAgentDetail();
        
        // Set up auto-refresh
        this.setupAutoRefresh();
        
        // Set up connection monitoring
        this.setupConnectionMonitoring();
        
        // Set up event listeners
        this.setupEventListeners();
        
        console.log(`Agent Detail Dashboard initialized for agent: ${this.agentId}`);
    }

    loadAgentConfig() {
        const agentDataElement = document.getElementById('agent-data');
        if (agentDataElement) {
            try {
                const agentData = JSON.parse(agentDataElement.textContent);
                this.agentId = agentData.agent_id;
                this.agentName = agentData.agent_name;
            } catch (error) {
                console.error('Error parsing agent data:', error);
            }
        }
    }

    setupEventListeners() {
        // Handle table header clicks for sorting
        document.addEventListener('click', (e) => {
            const header = e.target.closest('th[data-sort]');
            if (header) {
                const column = header.dataset.sort;
                this.sortTable(column);
            }
        });
        
        // Handle page visibility changes
        document.addEventListener('visibilitychange', () => {
            if (document.hidden) {
                this.pauseRefresh();
            } else {
                this.resumeRefresh();
            }
        });
        
        // Handle online/offline status
        window.addEventListener('online', () => {
            this.updateConnectionStatus(true);
            this.loadAgentDetail();
        });
        
        window.addEventListener('offline', () => {
            this.updateConnectionStatus(false);
        });
    }

    async loadAgentDetail() {
        console.log(`Loading agent detail for: ${this.agentId}`);
        
        try {
            this.showLoading();
            
            const response = await this.fetchWithTimeout(`/api/agents/${this.agentId}`, {
                method: 'GET',
                headers: {
                    'Accept': 'application/json',
                    'Content-Type': 'application/json'
                }
            });
            
            if (!response.ok) {
                if (response.status === 404) {
                    throw new Error('Agent not found');
                } else {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }
            }
            
            const data = await response.json();
            
            this.renderAgentSummary(data.agent);
            this.renderPositionsTable(data.agent.positions);
            this.renderPoliticiansSection(data.agent.politicians);
            this.updateLastUpdateTime();
            this.updateConnectionStatus(true);
            
            this.retryCount = 0; // Reset retry count on success
            
        } catch (error) {
            console.error('Error loading agent detail:', error);
            this.handleError(error);
        }
    }

    renderAgentSummary(agent) {
        // Update header
        const portfolioValueElement = document.getElementById('total-value');
        if (portfolioValueElement) {
            portfolioValueElement.textContent = agent.total_value_formatted || '$0.00';
        }
        
        // Update summary cards
        const summaryElements = {
            'agent-type': agent.type || 'Unknown',
            'politicians-count': Array.isArray(agent.politicians) ? agent.politicians.length : 0,
            'positions-count': agent.position_count || 0,
            'daily-return': this.formatPercentage(agent.daily_return_pct),
            'total-return': this.formatPercentage(agent.total_return_pct)
        };
        
        Object.entries(summaryElements).forEach(([id, value]) => {
            const element = document.getElementById(id);
            if (element) {
                element.textContent = value;
                
                // Add color classes for returns
                if (id.includes('return')) {
                    element.className = `summary-value ${this.getReturnClass(
                        id === 'daily-return' ? agent.daily_return_pct : agent.total_return_pct
                    )}`;
                }
            }
        });
        
        // Show summary section
        const summarySection = document.getElementById('agent-summary');
        if (summarySection) {
            summarySection.style.display = 'grid';
            summarySection.classList.add('fade-in');
        }
    }

    renderPositionsTable(positions) {
        const tbody = document.getElementById('positions-tbody');
        const tableContainer = document.getElementById('table-container');
        const emptyState = document.getElementById('empty-state');
        
        if (!positions || positions.length === 0) {
            tableContainer.style.display = 'none';
            emptyState.style.display = 'flex';
            this.hideLoading();
            return;
        }
        
        // Sort positions
        const sortedPositions = this.sortPositions(positions);
        
        tbody.innerHTML = sortedPositions.map(position => `
            <tr class="position-row">
                <td class="font-medium">
                    ${this.escapeHtml(position.ticker || position.asset)}
                </td>
                <td class="text-right font-medium">
                    ${position.amount_formatted || position.market_value_formatted || this.formatCurrency(position.market_value)}
                </td>
                <td class="text-right">
                    ${position.nav_percent_formatted || this.formatPercentage(position.nav_percent)}
                </td>
                <td class="text-right ${this.getReturnClass(position.todays_pnl_percent)}">
                    ${position.todays_pnl_percent_formatted || this.formatPercentage(position.todays_pnl_percent)}
                </td>
                <td class="text-right ${this.getReturnClass(position.total_pnl_percent)}">
                    ${position.total_pnl_percent_formatted || this.formatPercentage(position.total_pnl_percent)}
                </td>
            </tr>
        `).join('');
        
        emptyState.style.display = 'none';
        tableContainer.style.display = 'block';
        this.hideLoading();
        
        // Add animation
        tbody.classList.add('fade-in');
        
        // Update sort indicators
        this.updateSortIndicators();
    }

    renderPoliticiansSection(politicians) {
        const politiciansSection = document.getElementById('politicians-section');
        const politiciansList = document.getElementById('politicians-list');
        
        if (!politicians || politicians.length === 0) {
            politiciansSection.style.display = 'none';
            return;
        }
        
        politiciansList.innerHTML = politicians.map(politician => 
            `<span class="politician-tag">${this.escapeHtml(politician)}</span>`
        ).join('');
        
        politiciansSection.style.display = 'block';
        politiciansSection.classList.add('fade-in');
    }

    sortPositions(positions) {
        return [...positions].sort((a, b) => {
            let aVal = a[this.sortColumn] || 0;
            let bVal = b[this.sortColumn] || 0;
            
            // Handle string values
            if (this.sortColumn === 'ticker' || this.sortColumn === 'asset') {
                aVal = String(aVal).toLowerCase();
                bVal = String(bVal).toLowerCase();
            }
            
            if (this.sortDirection === 'asc') {
                return aVal < bVal ? -1 : aVal > bVal ? 1 : 0;
            } else {
                return aVal > bVal ? -1 : aVal < bVal ? 1 : 0;
            }
        });
    }

    sortTable(column) {
        if (this.sortColumn === column) {
            // Toggle direction if same column
            this.sortDirection = this.sortDirection === 'asc' ? 'desc' : 'asc';
        } else {
            // New column, default to descending
            this.sortColumn = column;
            this.sortDirection = 'desc';
        }
        
        // Re-render table with new sort
        this.loadAgentDetail();
    }

    updateSortIndicators() {
        // Remove all existing sort indicators
        document.querySelectorAll('th[data-sort]').forEach(header => {
            header.classList.remove('sort-asc', 'sort-desc');
        });
        
        // Add indicator to current sort column
        const currentHeader = document.querySelector(`th[data-sort="${this.sortColumn}"]`);
        if (currentHeader) {
            currentHeader.classList.add(`sort-${this.sortDirection}`);
        }
    }

    updateConnectionStatus(isConnected) {
        const indicator = document.getElementById('connection-indicator');
        const text = document.getElementById('connection-text');
        
        if (indicator) {
            indicator.className = `connection-indicator ${isConnected ? '' : 'disconnected'}`;
        }
        
        if (text) {
            text.textContent = isConnected ? 'Connected' : 'Disconnected';
        }
    }

    updateLastUpdateTime() {
        const lastUpdateElement = document.getElementById('last-update');
        if (lastUpdateElement) {
            const now = new Date();
            lastUpdateElement.textContent = `Last updated: ${now.toLocaleTimeString()}`;
        }
    }

    setupAutoRefresh() {
        // Clear existing interval
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
        }
        
        // Set up new interval
        this.refreshInterval = setInterval(() => {
            if (!document.hidden) {
                this.loadAgentDetail();
            }
        }, this.refreshRate);
        
        console.log(`Auto-refresh set up with ${this.refreshRate / 1000}s interval`);
    }

    pauseRefresh() {
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
            this.refreshInterval = null;
            console.log('Auto-refresh paused');
        }
    }

    resumeRefresh() {
        if (!this.refreshInterval) {
            this.setupAutoRefresh();
            console.log('Auto-refresh resumed');
        }
    }

    setupConnectionMonitoring() {
        // Monitor API connectivity
        this.connectionCheckInterval = setInterval(async () => {
            try {
                const response = await this.fetchWithTimeout('/api/health', { timeout: 5000 });
                this.updateConnectionStatus(response.ok);
            } catch (error) {
                this.updateConnectionStatus(false);
            }
        }, 30000); // Check every 30 seconds
    }

    async fetchWithTimeout(url, options = {}) {
        const timeout = options.timeout || this.connectionTimeout;
        
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), timeout);
        
        try {
            const response = await fetch(url, {
                ...options,
                signal: controller.signal
            });
            clearTimeout(timeoutId);
            return response;
        } catch (error) {
            clearTimeout(timeoutId);
            throw error;
        }
    }

    showLoading() {
        const loading = document.getElementById('loading-container');
        const table = document.getElementById('table-container');
        const error = document.getElementById('error-container');
        const emptyState = document.getElementById('empty-state');
        
        if (loading) loading.style.display = 'flex';
        if (table) table.style.display = 'none';
        if (error) error.style.display = 'none';
        if (emptyState) emptyState.style.display = 'none';
    }

    hideLoading() {
        const loading = document.getElementById('loading-container');
        if (loading) loading.style.display = 'none';
    }

    handleError(error) {
        const errorContainer = document.getElementById('error-container');
        const errorText = document.getElementById('error-text');
        
        this.hideLoading();
        
        if (errorText) {
            let errorMessage = 'Unable to load agent details. ';
            
            if (error.message === 'Agent not found') {
                errorMessage = 'The requested agent could not be found.';
            } else if (error.name === 'AbortError') {
                errorMessage += 'Request timed out.';
            } else if (error.message.includes('Failed to fetch')) {
                errorMessage += 'Network connection error.';
            } else {
                errorMessage += error.message;
            }
            
            errorText.textContent = errorMessage;
        }
        
        if (errorContainer) {
            errorContainer.style.display = 'flex';
        }
        
        this.updateConnectionStatus(false);
        
        // Implement exponential backoff for retries (except for 404s)
        if (error.message !== 'Agent not found') {
            this.retryCount++;
            if (this.retryCount < this.maxRetries) {
                const retryDelay = Math.min(1000 * Math.pow(2, this.retryCount), 30000);
                console.log(`Retrying in ${retryDelay / 1000} seconds... (attempt ${this.retryCount}/${this.maxRetries})`);
                
                setTimeout(() => {
                    this.loadAgentDetail();
                }, retryDelay);
            }
        }
    }

    getReturnClass(returnPct) {
        if (!returnPct && returnPct !== 0) return 'return-neutral';
        if (returnPct > 0) return 'return-positive';
        if (returnPct < 0) return 'return-negative';
        return 'return-neutral';
    }

    formatCurrency(amount) {
        if (amount === null || amount === undefined) return '$0.00';
        return `$${Number(amount).toFixed(2)}`;
    }

    formatPercentage(percent, decimals = 2) {
        if (percent === null || percent === undefined) return '0.00%';
        const value = Number(percent).toFixed(decimals);
        return `${value >= 0 ? '+' : ''}${value}%`;
    }

    formatNumber(num, decimals = 2) {
        if (num === null || num === undefined) return '0';
        return Number(num).toFixed(decimals);
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text || '';
        return div.innerHTML;
    }

    destroy() {
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
        }
        
        if (this.connectionCheckInterval) {
            clearInterval(this.connectionCheckInterval);
        }
        
        console.log('Agent Detail Dashboard destroyed');
    }
}

// Global functions
function loadAgentDetail() {
    if (window.agentDashboard) {
        window.agentDashboard.loadAgentDetail();
    }
}

function goBack() {
    // Try to use browser history first
    if (window.history.length > 1) {
        window.history.back();
    } else {
        // Fallback to dashboard home
        window.location.href = '/';
    }
}

// Initialize dashboard when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    window.agentDashboard = new AgentDetailDashboard();
});

// Clean up when page unloads
window.addEventListener('beforeunload', function() {
    if (window.agentDashboard) {
        window.agentDashboard.destroy();
    }
});
