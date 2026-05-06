'use strict';

(function () {
    let cardColor = config.colors.white;
    let headingColor = config.colors.headingColor;
    let axisColor = config.colors.axisColor;
    let borderColor = config.colors.borderColor;

    // Default placeholders (will be replaced by API)
    let attendanceData = {
        weekly: [12, 18, 15, 22, 28, 25, 20],
        previous_week: [10, 14, 12, 18, 22, 20, 16],
        labels: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
    };

    let visitorData = [24, 21, 30, 22, 42, 26, 35, 29];
    let tagData = { online: 85, offline: 15, maintenance: 50, defective: 0 };
    let successRate = 78;
    let weeklyPercentage = 65;

    // ============================================
    // 1. Attendance Chart
    // ============================================
    const attendanceChartEl = document.querySelector('#totalRevenueChart');

    if (attendanceChartEl) {
        window.attendanceChart = new ApexCharts(attendanceChartEl, {
            series: [
                { name: 'This Week', data: attendanceData.weekly },
                { name: 'Previous Week', data: attendanceData.previous_week }
            ],
            chart: { height: 300, type: 'bar', toolbar: { show: false } },
            plotOptions: {
                bar: { columnWidth: '45%', borderRadius: 8 }
            },
            colors: [config.colors.primary, config.colors.info],
            xaxis: { categories: attendanceData.labels },
            yaxis: { min: 0 }
        });

        window.attendanceChart.render();
    }

    // ============================================
    // 2. Success Rate Chart
    // ============================================
    const growthChartEl = document.querySelector('#growthChart');

    if (growthChartEl) {
        window.growthChart = new ApexCharts(growthChartEl, {
            series: [successRate],
            chart: { height: 240, type: 'radialBar' },
            labels: ['Success Rate']
        });

        window.growthChart.render();
    }

    // ============================================
    // 3. Tag Chart
    // ============================================
    const tagChartEl = document.querySelector('#orderStatisticsChart');

    if (tagChartEl) {
        window.tagStatisticsChart = new ApexCharts(tagChartEl, {
            chart: { type: 'donut' },
            labels: ['Online', 'Offline', 'Maintenance', 'Defective'],
            series: [
                tagData.online,
                tagData.offline,
                tagData.maintenance,
                tagData.defective
            ]
        });

        window.tagStatisticsChart.render();
    }

    // ============================================
    // 4. Visitor Chart
    // ============================================
    const visitorChartEl = document.querySelector('#incomeChart');

    if (visitorChartEl) {
        window.visitorTrendChart = new ApexCharts(visitorChartEl, {
            series: [{ data: visitorData }],
            chart: { height: 215, type: 'area' },
            xaxis: {
                categories: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun', 'Today']
            }
        });

        window.visitorTrendChart.render();
    }

    // ============================================
    // 5. Weekly Percentage
    // ============================================
    const weeklyVisitorEl = document.querySelector('#expensesOfWeek');

    if (weeklyVisitorEl) {
        window.weeklyVisitorChart = new ApexCharts(weeklyVisitorEl, {
            series: [weeklyPercentage],
            chart: { type: 'radialBar', height: 60 }
        });

        window.weeklyVisitorChart.render();
    }

})();


// ============================================
// REAL-TIME UPDATE FUNCTIONS
// ============================================

function updateAttendanceChart(data) {
    if (window.attendanceChart) {
        window.attendanceChart.updateSeries([
            { name: 'This Week', data: data.weekly },
            { name: 'Previous Week', data: data.previous_week }
        ]);
        window.attendanceChart.updateOptions({
            xaxis: { categories: data.labels }
        });
    }
}

function updateTagChart(data) {
    if (window.tagStatisticsChart) {
        window.tagStatisticsChart.updateSeries([
            data.online,
            data.offline,
            data.maintenance,
            data.defective
        ]);
    }
}

function updateVisitorChart(data) {
    if (window.visitorTrendChart) {
        window.visitorTrendChart.updateSeries([{ data: data }]);
    }
}

function updateSuccessRate(rate) {
    if (window.growthChart) {
        window.growthChart.updateSeries([rate]);
    }
}

function updateWeeklyVisitorPercentage(val) {
    if (window.weeklyVisitorChart) {
        window.weeklyVisitorChart.updateSeries([val]);
    }
}


// ============================================
// FETCH REAL DATA FROM DJANGO
// ============================================

function fetchRealTimeChartData() {
    fetch('/dashboard/chart-data/')  // ✅ FIXED URL
        .then(res => res.json())
        .then(data => {
            if (data.attendance) updateAttendanceChart(data.attendance);
            if (data.tags) updateTagChart(data.tags);
            if (data.visitors) {
                updateVisitorChart(data.visitors.daily_data);
                updateWeeklyVisitorPercentage(data.visitors.weekly_percentage);
            }
            if (data.success_rate !== undefined) {
                updateSuccessRate(data.success_rate);
            }
        })
        .catch(err => console.error('Chart fetch error:', err));
}

// Optional auto refresh
// setInterval(fetchRealTimeChartData, 30000);