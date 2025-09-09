/**
 * Overview Dashboard JavaScript
 * Handles agent overview dashboard functionality including data loading,
 * auto-refresh, navigation, and market status display.
 */

class OverviewDashboard {
    constructor() {
        this.refreshInterval = null;
        this.refreshRate = 60000; // 60 seconds
        this.isMarketHours = false;
        this.connectionTimeout = 10000; // 10 seconds
        this.retryCount = 0;
        this.maxRetries = 3;
        
        this.init();
    }

    init() {
        console.log('Initializing Overview Dashboard...');
        
        // Load initial data
        this.loadAgentData();
        this.loadSystemStatus();
        
        // Set up auto-refresh
        this.setupAutoRefresh();
        
        // Set up connection monitoring
        this.setupConnectionMonitoring();
        
        // Set up event listeners
        this.setupEventListeners();
        
        console.log('Overview Dashboard initialized');
    }

    setupEventListeners() {
        // Handle table row clicks for navigation
        document.addEventListener('click', (e) => {
            const row = e.target.closest('tr[data-agent-id]');
            if (row) {
                const agentId = row.dataset.agentId;
                this.navigateToAgent(agentId);
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
            this.loadAgentData();
        });
        
        window.addEventListener('offline', () => {
            this.updateConnectionStatus(false);
        });
    }

    async loadAgentData() {
        console.log('Loading agent data...');
        
        try {
            this.showLoading();
            
            const response = await this.fetchWithTimeout('/api/agents', {
                method: 'GET',
                headers: {
                    'Accept': 'application/json',
                    'Content-Type': 'application/json'
                }
            });
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            
            this.renderAgentsTable(data.agents);
            this.renderSummaryStats(data.agents);
            this.updateLastUpdateTime();
            this.updateConnectionStatus(true);
            
            this.retryCount = 0; // Reset retry count on success
            
        } catch (error) {
            console.error('Error loading agent data:', error);
            this.handleError(error);
        }
    }

    async loadSystemStatus() {
        try {
            const response = await this.fetchWithTimeout('/api/system/status');
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            
            this.updateMarketStatus(data.market);
            this.isMarketHours = data.market.is_open;
            
            // Adjust refresh rate based on market hours
            this.adjustRefreshRate();
            
        } catch (error) {
            console.error('Error loading system status:', error);
            // Don't show error for system status - it's not critical
        }
    }

    renderAgentsTable(agents) {
        const tbody = document.getElementById('agents-tbody');
        const tableContainer = document.getElementById('table-container');
        
        if (!agents || agents.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="7" class="text-center text-muted">
                        No agents configured or data available
                    </td>
                </tr>
            `;
            tableContainer.style.display = 'block';
            this.hideLoading();
            return;
        }
        
        tbody.innerHTML = agents.map(agent => `
            <tr data-agent-id="${agent.agent_id}" class="agent-row">
                <td>
                    <div>
                        <div class="font-medium">${this.escapeHtml(agent.name)}</div>
                        <div class="text-muted" style="font-size: 0.875rem;">
                            ${this.escapeHtml(agent.description || '')}
                        </div>
                    </div>
                </td>
                <td>
                    <span class="status-badge ${agent.type === 'committee' ? 'active' : 'inactive'}">
                        ${agent.type}
                    </span>
                </td>
                <td class="font-medium">
                    ${agent.total_value_formatted || '$0.00'}
                </td>
                <td class="text-center">
                    ${agent.position_count || 0}
                </td>
                <td class="${this.getReturnClass(agent.daily_return_pct)}">
                    ${agent.daily_return_formatted || '0.00%'}
                </td>
                <td class="${this.getReturnClass(agent.total_return_pct)}">
                    ${agent.total_return_formatted || '0.00%'}
                </td>
                <td>
                    <span class="status-badge ${agent.enabled ? 'active' : 'inactive'}">
                        ${agent.enabled ? 'Active' : 'Inactive'}
                    </span>
                </td>
            </tr>
        `).join('');
        
        tableContainer.style.display = 'block';
        this.hideLoading();
        
        // Add animation
        tbody.classList.add('fade-in');
    }

    renderSummaryStats(agents) {
        const summaryStats = document.getElementById('summary-stats');
        
        if (!agents || agents.length === 0) {
            summaryStats.style.display = 'none';
            return;
        }
        
        // Calculate summary statistics
        const totalAgents = agents.length;
        const totalValue = agents.reduce((sum, agent) => sum + (agent.total_value || 0), 0);
        const totalPositions = agents.reduce((sum, agent) => sum + (agent.position_count || 0), 0);
        
        // Find best performer
        const bestPerformer = agents.reduce((best, agent) => {
            const agentReturn = agent.total_return_pct || 0;
            const bestReturn = best ? (best.total_return_pct || 0) : -Infinity;
            return agentReturn > bestReturn ? agent : best;
        }, null);
        
        // Update stat values
        document.getElementById('total-agents').textContent = totalAgents;
        document.getElementById('total-value').textContent = this.formatCurrency(totalValue);
        document.getElementById('total-positions').textContent = totalPositions;
        document.getElementById('best-performer').textContent = 
            bestPerformer ? bestPerformer.name : '-';
        
        summaryStats.style.display = 'grid';
        summaryStats.classList.add('fade-in');
    }

    updateMarketStatus(marketData) {
        const statusElement = document.getElementById('market-status');
        const indicatorElement = document.getElementById('market-indicator');
        const textElement = document.getElementById('market-text');
        
        if (!statusElement || !indicatorElement || !textElement) return;
        
        const isOpen = marketData.is_open;
        const isWeekend = marketData.is_weekend;
        const isHoliday = marketData.is_holiday;
        
        // Update indicator class
        indicatorElement.className = 'status-indicator';
        
        let statusText = 'Market Closed';
        if (isOpen) {
            statusText = 'Market Open';
            indicatorElement.classList.add('open');
        } else if (isWeekend) {
            statusText = 'Weekend';
            indicatorElement.classList.add('closed');
        } else if (isHoliday) {
            statusText = 'Holiday';
            indicatorElement.classList.add('closed');
        } else {
            indicatorElement.classList.add('closed');
        }
        
        textElement.textContent = statusText;
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
                this.loadAgentData();
                
                // Also refresh system status less frequently
                if (Math.random() < 0.1) { // 10% chance each refresh
                    this.loadSystemStatus();
                }
            }
        }, this.refreshRate);
        
        console.log(`Auto-refresh set up with ${this.refreshRate / 1000}s interval`);
    }

    adjustRefreshRate() {
        // Refresh more frequently during market hours
        const newRefreshRate = this.isMarketHours ? 60000 : 300000; // 1min vs 5min
        
        if (newRefreshRate !== this.refreshRate) {
            this.refreshRate = newRefreshRate;
            this.setupAutoRefresh();
            console.log(`Refresh rate adjusted to ${this.refreshRate / 1000}s`);
        }
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

    navigateToAgent(agentId) {
        if (agentId) {
            window.location.href = `/agent/${agentId}`;
        }
    }

    showLoading() {
        const loading = document.getElementById('loading-container');
        const table = document.getElementById('table-container');
        const error = document.getElementById('error-container');
        const stats = document.getElementById('summary-stats');
        
        if (loading) loading.style.display = 'flex';
        if (table) table.style.display = 'none';
        if (error) error.style.display = 'none';
        if (stats) stats.style.display = 'none';
    }

    hideLoading() {
        const loading = document.getElementById('loading-container');
        if (loading) loading.style.display = 'none';
    }

    handleError(error) {
        const errorContainer = document.getElementById('error-container');
        const errorText = document.getElementById('error-text');
        const loading = document.getElementById('loading-container');
        const table = document.getElementById('table-container');
        
        this.hideLoading();
        
        if (errorText) {
            let errorMessage = 'Unable to load agent data. ';
            
            if (error.name === 'AbortError') {
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
        
        if (table) {
            table.style.display = 'none';
        }
        
        this.updateConnectionStatus(false);
        
        // Implement exponential backoff for retries
        this.retryCount++;
        if (this.retryCount < this.maxRetries) {
            const retryDelay = Math.min(1000 * Math.pow(2, this.retryCount), 30000); // Max 30 seconds
            console.log(`Retrying in ${retryDelay / 1000} seconds... (attempt ${this.retryCount}/${this.maxRetries})`);
            
            setTimeout(() => {
                this.loadAgentData();
            }, retryDelay);
        }
    }

    getReturnClass(returnPct) {
        if (returnPct > 0) return 'return-positive';
        if (returnPct < 0) return 'return-negative';
        return 'return-neutral';
    }

    formatCurrency(amount) {
        if (amount >= 1000000) {
            return `$${(amount / 1000000).toFixed(1)}M`;
        } else if (amount >= 1000) {
            return `$${(amount / 1000).toFixed(1)}K`;
        } else {
            return `$${amount.toFixed(2)}`;
        }
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    destroy() {
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
        }
        
        if (this.connectionCheckInterval) {
            clearInterval(this.connectionCheckInterval);
        }
        
        console.log('Overview Dashboard destroyed');
    }
}

// Global function for retry button
function loadAgentData() {
    if (window.dashboard) {
        window.dashboard.loadAgentData();
    }
}

// Initialize dashboard when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    window.dashboard = new OverviewDashboard();
});

// Clean up when page unloads
window.addEventListener('beforeunload', function() {
    if (window.dashboard) {
        window.dashboard.destroy();
    }
});