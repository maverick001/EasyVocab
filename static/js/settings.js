/**
 * Settings page: load/save settings and draw the review-history chart.
 * The chart is plain SVG built with DOM calls (no library, no HTML strings).
 */
(function () {
    'use strict';

    const SVG_NS = 'http://www.w3.org/2000/svg';
    const form = document.getElementById('settingsForm');
    const statusEl = document.getElementById('saveStatus');
    const chartEl = document.getElementById('historyChart');
    const summaryEl = document.getElementById('historySummary');
    const rangeButtons = document.querySelectorAll('.range-btn');
    let currentDays = 30;

    // Same key as the vocab and quiz pages, so dark mode carries over
    try {
        if (localStorage.getItem('bkdict-theme') === 'dark') {
            document.body.classList.add('dark-mode');
        }
    } catch (e) { /* storage blocked: stay light */ }

    // GUI theme: same localStorage key and file naming as the vocab page
    // (applyGuiTheme in app.js). 'default' means no theme file.
    function applyGuiTheme() {
        const themeLink = document.getElementById('themeStylesheet');
        if (!themeLink) return;
        let themeName = 'default';
        try {
            themeName = localStorage.getItem('bkdict-gui-theme') || 'default';
        } catch (e) { /* storage blocked: default theme */ }
        // Only names that exist as theme files, so a stray value cannot build a URL
        let versions = {};
        try {
            versions = JSON.parse(themeLink.dataset.versions || '{}');
        } catch (e) { /* no versions: no ?v= */ }
        if (themeName === 'default' || !Object.prototype.hasOwnProperty.call(versions, themeName)) {
            themeLink.href = '';
            return;
        }
        const version = versions[themeName];
        themeLink.href = `/static/css/themes/theme-${themeName}.css${version ? `?v=${version}` : ''}`;
    }
    applyGuiTheme();

    function setStatus(text, isError) {
        statusEl.textContent = text;
        statusEl.classList.toggle('error', Boolean(isError));
    }

    function fillForm(settings) {
        form.daily_target.value = settings.daily_target;
        form.debt_enabled.checked = Boolean(settings.debt_enabled);
        form.debt_start_date.value = settings.debt_start_date || '';
        form.timezone.value = settings.timezone || '';
        form.quiz_choice_count.value = settings.quiz_choice_count;
        form.quiz_session_size.value = settings.quiz_session_size;
    }

    async function loadSettings() {
        try {
            const response = await fetch('/api/settings');
            const data = await response.json();
            if (!data.success) throw new Error(data.error || 'Could not load settings');
            fillForm(data.settings);
        } catch (error) {
            setStatus(error.message, true);
        }
    }

    async function saveSettings(event) {
        event.preventDefault();
        setStatus('Saving…', false);
        const body = {
            daily_target: form.daily_target.value.trim(),
            debt_enabled: form.debt_enabled.checked,
            debt_start_date: form.debt_start_date.value,
            timezone: form.timezone.value.trim(),
            quiz_choice_count: form.quiz_choice_count.value.trim(),
            quiz_session_size: form.quiz_session_size.value.trim()
        };
        try {
            const response = await fetch('/api/settings', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(body)
            });
            const data = await response.json();
            if (!data.success) throw new Error(data.error || 'Could not save settings');
            fillForm(data.settings);
            setStatus('Saved', false);
            loadHistory(currentDays);
        } catch (error) {
            setStatus(error.message, true);
        }
    }

    function svgEl(name, attrs) {
        const el = document.createElementNS(SVG_NS, name);
        Object.keys(attrs || {}).forEach(key => el.setAttribute(key, attrs[key]));
        return el;
    }

    function shortDate(iso) {
        const parts = iso.split('-');
        return `${Number(parts[2])}/${Number(parts[1])}`;
    }

    function drawChart(history, target) {
        const width = 640, height = 240;
        const pad = { left: 38, right: 10, top: 12, bottom: 26 };
        const plotW = width - pad.left - pad.right;
        const plotH = height - pad.top - pad.bottom;
        const maxCount = Math.max(target, ...history.map(d => d.review_count));
        const yMax = Math.ceil((maxCount * 1.1) / 10) * 10 || 10;
        const y = value => pad.top + plotH - (value / yMax) * plotH;

        const svg = svgEl('svg', {
            viewBox: `0 0 ${width} ${height}`,
            role: 'img',
            preserveAspectRatio: 'xMidYMid meet'
        });

        // Horizontal grid lines and y labels
        [0, 0.5, 1].forEach(fraction => {
            const value = Math.round(yMax * fraction);
            svg.appendChild(svgEl('line', {
                x1: pad.left, x2: width - pad.right, y1: y(value), y2: y(value),
                class: 'chart-grid'
            }));
            const label = svgEl('text', {
                x: pad.left - 6, y: y(value) + 4, 'text-anchor': 'end', class: 'chart-label'
            });
            label.textContent = String(value);
            svg.appendChild(label);
        });

        // Bars: green at or above target, blue below
        const slot = plotW / history.length;
        const barW = Math.max(slot * 0.7, 1.5);
        history.forEach((day, index) => {
            const x = pad.left + slot * index + (slot - barW) / 2;
            const barH = (day.review_count / yMax) * plotH;
            const bar = svgEl('rect', {
                x: x, y: y(day.review_count), width: barW, height: Math.max(barH, 0),
                rx: 1.5,
                class: day.review_count >= target ? 'chart-bar met' : 'chart-bar'
            });
            const tip = svgEl('title', {});
            tip.textContent = `${day.date}: ${day.review_count}`;
            bar.appendChild(tip);
            svg.appendChild(bar);
        });

        // Dashed target line
        svg.appendChild(svgEl('line', {
            x1: pad.left, x2: width - pad.right, y1: y(target), y2: y(target),
            class: 'chart-target'
        }));
        const targetLabel = svgEl('text', {
            x: width - pad.right, y: y(target) - 4, 'text-anchor': 'end', class: 'chart-label'
        });
        targetLabel.textContent = `Target ${target}`;
        svg.appendChild(targetLabel);

        // X labels: first, middle, last
        [0, Math.floor((history.length - 1) / 2), history.length - 1].forEach((index, i) => {
            const label = svgEl('text', {
                x: pad.left + slot * index + slot / 2,
                y: height - 8,
                'text-anchor': i === 0 ? 'start' : (i === 2 ? 'end' : 'middle'),
                class: 'chart-label'
            });
            label.textContent = shortDate(history[index].date);
            svg.appendChild(label);
        });

        chartEl.replaceChildren(svg);
    }

    async function loadHistory(days) {
        currentDays = days;
        rangeButtons.forEach(btn => btn.classList.toggle('active', Number(btn.dataset.days) === days));
        try {
            const response = await fetch(`/api/review-history?days=${days}`);
            const data = await response.json();
            if (!data.success) throw new Error(data.error || 'Could not load history');
            drawChart(data.history, data.target);

            const total = data.history.reduce((sum, d) => sum + d.review_count, 0);
            const hit = data.history.filter(d => d.review_count >= data.target).length;
            summaryEl.textContent =
                `Average ${(total / data.history.length).toFixed(1)} per day · ` +
                `target reached on ${hit} of ${data.history.length} days.`;
        } catch (error) {
            chartEl.textContent = error.message;
            summaryEl.textContent = '';
        }
    }

    form.addEventListener('submit', saveSettings);
    rangeButtons.forEach(btn => btn.addEventListener('click', () => loadHistory(Number(btn.dataset.days))));
    loadSettings();
    loadHistory(currentDays);
})();
