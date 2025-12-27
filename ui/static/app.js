/**
 * MCP-BTR Tool Selector Frontend
 */

// State
let allTools = {};
let enabledTools = new Set();

// DOM Elements
const toolsContainer = document.getElementById('tools-container');
const enabledCount = document.getElementById('enabled-count');
const totalCount = document.getElementById('total-count');
const budgetStatus = document.getElementById('budget-status');
const budgetIndicator = document.querySelector('.budget-indicator');
const presetSelect = document.getElementById('preset-select');

// Budget thresholds
const BUDGET_OK = 30;
const BUDGET_WARNING = 40;

/**
 * Initialize the application
 */
async function init() {
    await Promise.all([
        loadTools(),
        loadPresets()
    ]);

    // Set up event listeners
    document.getElementById('load-preset-btn').addEventListener('click', loadSelectedPreset);
    document.getElementById('select-none-btn').addEventListener('click', disableAll);
    document.getElementById('refresh-btn').addEventListener('click', loadTools);
}

/**
 * Load all tools from the API
 */
async function loadTools() {
    toolsContainer.innerHTML = '<p class="loading">Loading tools...</p>';

    try {
        const response = await fetch('/api/tools');
        const data = await response.json();

        if (!data.success) {
            throw new Error(data.error || 'Failed to load tools');
        }

        allTools = data.servers;
        updateStats(data.enabled_count, data.total);
        renderTools();

    } catch (error) {
        toolsContainer.innerHTML = `<p class="loading">Error: ${error.message}</p>`;
    }
}

/**
 * Load available presets
 */
async function loadPresets() {
    try {
        const response = await fetch('/api/presets');
        const data = await response.json();

        if (data.success && data.presets) {
            presetSelect.innerHTML = '<option value="">Select preset...</option>';
            data.presets.forEach(preset => {
                const option = document.createElement('option');
                option.value = preset.name;
                option.textContent = `${preset.name} (${preset.tool_count} tools)`;
                presetSelect.appendChild(option);
            });
        }
    } catch (error) {
        console.error('Failed to load presets:', error);
    }
}

/**
 * Load the selected preset
 */
async function loadSelectedPreset() {
    const presetName = presetSelect.value;
    if (!presetName) return;

    try {
        const response = await fetch('/api/presets/load', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name: presetName })
        });

        const data = await response.json();
        if (data.success) {
            await loadTools();
        }
    } catch (error) {
        console.error('Failed to load preset:', error);
    }
}

/**
 * Disable all tools
 */
async function disableAll() {
    try {
        const response = await fetch('/api/update', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ tools: [] })
        });

        const data = await response.json();
        if (data.success) {
            await loadTools();
        }
    } catch (error) {
        console.error('Failed to disable all:', error);
    }
}

/**
 * Toggle a specific tool
 */
async function toggleTool(toolName) {
    try {
        const response = await fetch('/api/tools/toggle', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ tool: toolName })
        });

        const data = await response.json();
        if (data.success) {
            // Update local state and UI
            const checkbox = document.querySelector(`input[data-tool="${toolName}"]`);
            if (checkbox) {
                checkbox.checked = data.enabled;
            }
            await loadTools(); // Refresh stats
        }
    } catch (error) {
        console.error('Failed to toggle tool:', error);
    }
}

/**
 * Select/deselect all tools in a server
 */
async function toggleServer(serverName, enable) {
    const tools = allTools[serverName] || [];
    const toolNames = tools.map(t => t.name);

    // Get current enabled tools
    const currentResponse = await fetch('/api/current');
    const currentData = await currentResponse.json();
    let currentTools = new Set(currentData.tools || []);

    if (enable) {
        toolNames.forEach(t => currentTools.add(t));
    } else {
        toolNames.forEach(t => currentTools.delete(t));
    }

    try {
        const response = await fetch('/api/update', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ tools: Array.from(currentTools) })
        });

        if ((await response.json()).success) {
            await loadTools();
        }
    } catch (error) {
        console.error('Failed to toggle server:', error);
    }
}

/**
 * Update stats display
 */
function updateStats(enabled, total) {
    enabledCount.textContent = enabled;
    totalCount.textContent = total;

    // Update budget indicator
    if (enabled <= BUDGET_OK) {
        budgetStatus.textContent = 'OK';
        budgetIndicator.className = 'stat budget-indicator';
    } else if (enabled <= BUDGET_WARNING) {
        budgetStatus.textContent = 'Warning';
        budgetIndicator.className = 'stat budget-indicator warning';
    } else {
        budgetStatus.textContent = 'Over';
        budgetIndicator.className = 'stat budget-indicator over';
    }
}

/**
 * Render all tools grouped by server
 */
function renderTools() {
    toolsContainer.innerHTML = '';

    for (const [serverName, tools] of Object.entries(allTools)) {
        const section = document.createElement('div');
        section.className = 'server-section';

        const enabledInServer = tools.filter(t => t.enabled).length;

        section.innerHTML = `
            <div class="server-header" onclick="this.parentElement.classList.toggle('collapsed')">
                <h2>
                    ${serverName}
                    <span class="server-count">${enabledInServer}/${tools.length}</span>
                </h2>
                <div class="server-actions">
                    <button class="btn btn-secondary" onclick="event.stopPropagation(); toggleServer('${serverName}', true)">All</button>
                    <button class="btn btn-secondary" onclick="event.stopPropagation(); toggleServer('${serverName}', false)">None</button>
                </div>
            </div>
            <div class="tools-list">
                ${tools.map(tool => `
                    <div class="tool-item">
                        <input type="checkbox"
                            data-tool="${tool.name}"
                            ${tool.enabled ? 'checked' : ''}
                            onchange="toggleTool('${tool.name}')">
                        <div class="tool-info">
                            <div class="tool-name">${tool.name}</div>
                            <div class="tool-description">${tool.description || 'No description'}</div>
                        </div>
                    </div>
                `).join('')}
            </div>
        `;

        toolsContainer.appendChild(section);
    }
}

// Initialize on load
document.addEventListener('DOMContentLoaded', init);
