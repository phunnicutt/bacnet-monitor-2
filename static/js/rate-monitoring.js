/**
 * BACmon Enhanced Rate Monitoring Visualization
 * 
 * This file provides advanced visualization for the BACmon rate monitoring
 * features, including anomaly detection visualization.
 */

// Create color constants for different chart elements
const CHART_COLORS = {
    normal: 'rgba(75, 192, 192, 0.6)',
    anomaly: 'rgba(255, 99, 132, 0.6)',
    threshold: 'rgba(255, 159, 64, 0.8)',
    statistical: 'rgba(153, 102, 255, 0.6)',
    trend: 'rgba(54, 162, 235, 0.6)',
    timePattern: 'rgba(255, 206, 86, 0.6)',
    baseline: 'rgba(201, 203, 207, 0.4)',
    borderNormal: 'rgb(75, 192, 192)',
    borderAnomaly: 'rgb(255, 99, 132)',
    borderThreshold: 'rgb(255, 159, 64)',
    borderStatistical: 'rgb(153, 102, 255)',
    borderTrend: 'rgb(54, 162, 235)',
    borderTimePattern: 'rgb(255, 206, 86)',
    borderBaseline: 'rgb(201, 203, 207)'
};

// Initialize charts on page load
document.addEventListener('DOMContentLoaded', function() {
    // Try to initialize charts if elements exist
    initializeCharts();
});

/**
 * Initialize all rate monitoring charts
 */
function initializeCharts() {
    // Initialize main rate chart if element exists
    const rateChartElement = document.getElementById('rate-chart');
    if (rateChartElement) {
        initializeRateChart(rateChartElement);
    }
    
    // Initialize anomaly history chart if element exists
    const anomalyChartElement = document.getElementById('anomaly-chart');
    if (anomalyChartElement) {
        initializeAnomalyChart(anomalyChartElement);
    }
    
    // Initialize anomaly type distribution chart if element exists
    const anomalyTypeChartElement = document.getElementById('anomaly-type-chart');
    if (anomalyTypeChartElement) {
        initializeAnomalyTypeChart(anomalyTypeChartElement);
    }
    
    // Initialize time distribution chart if element exists
    const timeDistributionChartElement = document.getElementById('time-distribution-chart');
    if (timeDistributionChartElement) {
        initializeTimeDistributionChart(timeDistributionChartElement);
    }
}

/**
 * Initialize the main rate chart showing values over time with anomalies highlighted
 * @param {HTMLCanvasElement} chartElement - The canvas element for the chart
 */
function initializeRateChart(chartElement) {
    // Get the chart data from the data attribute
    const chartDataElement = document.getElementById('rate-chart-data');
    if (!chartDataElement) {
        console.error('Rate chart data element not found');
        return;
    }
    
    try {
        const chartData = JSON.parse(chartDataElement.textContent);
        
        // Format data for Chart.js
        const labels = chartData.timestamps.map(ts => moment(ts * 1000).format('YYYY-MM-DD HH:mm:ss'));
        const values = chartData.values;
        const anomalies = chartData.anomalies || [];
        const thresholds = chartData.thresholds || [];
        
        // Create datasets for normal values and anomalies
        const datasets = [
            {
                label: 'Rate Values',
                data: values,
                backgroundColor: values.map((v, i) => 
                    anomalies.includes(i) ? CHART_COLORS.anomaly : CHART_COLORS.normal
                ),
                borderColor: values.map((v, i) => 
                    anomalies.includes(i) ? CHART_COLORS.borderAnomaly : CHART_COLORS.borderNormal
                ),
                borderWidth: 1,
                pointRadius: values.map((v, i) => 
                    anomalies.includes(i) ? 5 : 3
                ),
                pointHoverRadius: values.map((v, i) => 
                    anomalies.includes(i) ? 7 : 5
                )
            }
        ];
        
        // Add threshold line if available
        if (thresholds.length > 0 && thresholds[0]) {
            const thresholdValue = thresholds[0];
            datasets.push({
                label: 'Threshold',
                data: Array(values.length).fill(thresholdValue),
                borderColor: CHART_COLORS.borderThreshold,
                backgroundColor: 'transparent',
                borderWidth: 2,
                borderDash: [5, 5],
                pointRadius: 0,
                pointHoverRadius: 0,
                fill: false
            });
        }
        
        // Create the chart
        const ctx = chartElement.getContext('2d');
        const chart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: datasets
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: {
                        display: true,
                        text: 'Rate Monitoring with Anomaly Detection',
                        font: {
                            size: 16
                        }
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                const index = context.dataIndex;
                                let label = context.dataset.label || '';
                                if (label) {
                                    label += ': ';
                                }
                                label += context.parsed.y;
                                
                                // Add anomaly information if this is an anomaly
                                if (anomalies.includes(index) && chartData.anomalyDetails && chartData.anomalyDetails[index]) {
                                    const details = chartData.anomalyDetails[index];
                                    label += ` (Anomaly: ${details.types.join(', ')}, Score: ${details.score.toFixed(2)})`;
                                }
                                
                                return label;
                            }
                        }
                    },
                    legend: {
                        display: true,
                        position: 'top'
                    }
                },
                scales: {
                    x: {
                        title: {
                            display: true,
                            text: 'Time'
                        }
                    },
                    y: {
                        title: {
                            display: true,
                            text: 'Value'
                        },
                        beginAtZero: true
                    }
                },
                animation: {
                    duration: 1000
                }
            }
        });
    } catch (error) {
        console.error('Error initializing rate chart:', error);
    }
}

/**
 * Initialize the anomaly history chart
 * @param {HTMLCanvasElement} chartElement - The canvas element for the chart
 */
function initializeAnomalyChart(chartElement) {
    // Get the chart data from the data attribute
    const chartDataElement = document.getElementById('anomaly-chart-data');
    if (!chartDataElement) {
        console.error('Anomaly chart data element not found');
        return;
    }
    
    try {
        const chartData = JSON.parse(chartDataElement.textContent);
        
        // Format data for Chart.js
        const labels = chartData.timestamps.map(ts => moment(ts * 1000).format('YYYY-MM-DD HH:mm:ss'));
        const values = chartData.values;
        const anomalyTypes = chartData.anomalyTypes || [];
        
        // Create color mapping for anomaly types
        const typeColors = {
            'threshold': CHART_COLORS.threshold,
            'spike': CHART_COLORS.anomaly,
            'z_score': CHART_COLORS.statistical,
            'increasing_trend': CHART_COLORS.trend,
            'decreasing_trend': CHART_COLORS.trend,
            'time_pattern': CHART_COLORS.timePattern,
            'rate_of_change': CHART_COLORS.anomaly
        };
        
        // Create the chart
        const ctx = chartElement.getContext('2d');
        const chart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Anomaly Values',
                    data: values,
                    backgroundColor: anomalyTypes.map(types => {
                        // Use the color of the first anomaly type
                        if (types && types.length > 0) {
                            return typeColors[types[0]] || CHART_COLORS.anomaly;
                        }
                        return CHART_COLORS.anomaly;
                    }),
                    borderColor: anomalyTypes.map(types => {
                        // Use the border color of the first anomaly type
                        if (types && types.length > 0) {
                            return typeColors[types[0]].replace('0.6', '1') || CHART_COLORS.borderAnomaly;
                        }
                        return CHART_COLORS.borderAnomaly;
                    }),
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: {
                        display: true,
                        text: 'Anomaly History',
                        font: {
                            size: 16
                        }
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                const index = context.dataIndex;
                                let label = context.dataset.label || '';
                                if (label) {
                                    label += ': ';
                                }
                                label += context.parsed.y;
                                
                                // Add anomaly type information
                                if (anomalyTypes[index]) {
                                    label += ` (Types: ${anomalyTypes[index].join(', ')})`;
                                }
                                
                                return label;
                            }
                        }
                    },
                    legend: {
                        display: false
                    }
                },
                scales: {
                    x: {
                        title: {
                            display: true,
                            text: 'Time'
                        }
                    },
                    y: {
                        title: {
                            display: true,
                            text: 'Value'
                        },
                        beginAtZero: true
                    }
                },
                animation: {
                    duration: 1000
                }
            }
        });
    } catch (error) {
        console.error('Error initializing anomaly chart:', error);
    }
}

/**
 * Initialize the anomaly type distribution chart
 * @param {HTMLCanvasElement} chartElement - The canvas element for the chart
 */
function initializeAnomalyTypeChart(chartElement) {
    // Get the chart data from the data attribute
    const chartDataElement = document.getElementById('anomaly-type-chart-data');
    if (!chartDataElement) {
        console.error('Anomaly type chart data element not found');
        return;
    }
    
    try {
        const chartData = JSON.parse(chartDataElement.textContent);
        
        // Format data for Chart.js
        const labels = Object.keys(chartData);
        const values = Object.values(chartData);
        
        // Create color mapping for anomaly types
        const typeColors = {
            'threshold': CHART_COLORS.threshold,
            'spike': CHART_COLORS.anomaly,
            'z_score': CHART_COLORS.statistical,
            'increasing_trend': CHART_COLORS.trend,
            'decreasing_trend': CHART_COLORS.trend,
            'time_pattern': CHART_COLORS.timePattern,
            'rate_of_change': CHART_COLORS.anomaly
        };
        
        // Map colors to labels
        const backgroundColors = labels.map(label => typeColors[label] || CHART_COLORS.anomaly);
        const borderColors = labels.map(label => {
            const bgColor = typeColors[label] || CHART_COLORS.anomaly;
            return bgColor.replace('0.6', '1');
        });
        
        // Create the chart
        const ctx = chartElement.getContext('2d');
        const chart = new Chart(ctx, {
            type: 'pie',
            data: {
                labels: labels,
                datasets: [{
                    data: values,
                    backgroundColor: backgroundColors,
                    borderColor: borderColors,
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: {
                        display: true,
                        text: 'Anomaly Type Distribution',
                        font: {
                            size: 16
                        }
                    },
                    legend: {
                        display: true,
                        position: 'right'
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                const label = context.label || '';
                                const value = context.parsed || 0;
                                const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                const percentage = total > 0 ? Math.round((value / total) * 100) : 0;
                                return `${label}: ${value} (${percentage}%)`;
                            }
                        }
                    }
                },
                animation: {
                    duration: 1000
                }
            }
        });
    } catch (error) {
        console.error('Error initializing anomaly type chart:', error);
    }
}

/**
 * Initialize the time distribution chart
 * @param {HTMLCanvasElement} chartElement - The canvas element for the chart
 */
function initializeTimeDistributionChart(chartElement) {
    // Get the chart data from the data attribute
    const chartDataElement = document.getElementById('time-distribution-chart-data');
    if (!chartDataElement) {
        console.error('Time distribution chart data element not found');
        return;
    }
    
    try {
        const chartData = JSON.parse(chartDataElement.textContent);
        
        // Format data for Chart.js
        const labels = ['00:00', '01:00', '02:00', '03:00', '04:00', '05:00', 
                         '06:00', '07:00', '08:00', '09:00', '10:00', '11:00',
                         '12:00', '13:00', '14:00', '15:00', '16:00', '17:00',
                         '18:00', '19:00', '20:00', '21:00', '22:00', '23:00'];
        
        // Create the chart
        const ctx = chartElement.getContext('2d');
        const chart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Anomalies by Hour',
                    data: chartData.hourDistribution,
                    backgroundColor: CHART_COLORS.anomaly,
                    borderColor: CHART_COLORS.borderAnomaly,
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: {
                        display: true,
                        text: 'Anomaly Time Distribution',
                        font: {
                            size: 16
                        }
                    },
                    legend: {
                        display: true,
                        position: 'top'
                    }
                },
                scales: {
                    x: {
                        title: {
                            display: true,
                            text: 'Hour of Day'
                        }
                    },
                    y: {
                        title: {
                            display: true,
                            text: 'Number of Anomalies'
                        },
                        beginAtZero: true
                    }
                },
                animation: {
                    duration: 1000
                }
            }
        });
    } catch (error) {
        console.error('Error initializing time distribution chart:', error);
    }
}

/**
 * Update charts with new data
 * @param {Object} data - The new data for the charts
 */
function updateCharts(data) {
    // Update implementation will be added when real-time updates are needed
    console.log('Chart update functionality to be implemented');
} 