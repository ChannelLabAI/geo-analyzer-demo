/**
 * GEO Analyzer P1 Features
 * 1. Screenshot Evidence Viewer
 * 2. PDF Report Export
 * 3. LLMrefs Citation Source Integration
 */

// ============================================
// 1. SCREENSHOT EVIDENCE VIEWER MODAL
// ============================================

function initScreenshotViewer() {
    // Create modal HTML
    const modal = document.createElement('div');
    modal.id = 'screenshot-modal';
    modal.className = 'screenshot-modal';
    modal.innerHTML = `
        <div class="modal-overlay" onclick="closeScreenshotModal()"></div>
        <div class="modal-content">
            <button class="modal-close" onclick="closeScreenshotModal()">✕</button>

            <div class="modal-header">
                <h3 id="screenshot-title">AI Response Evidence</h3>
                <p id="screenshot-platform" class="modal-platform"></p>
            </div>

            <div class="modal-body">
                <div class="screenshot-container">
                    <img id="screenshot-image" src="" alt="AI Response Screenshot">
                </div>
                <div class="response-transcript">
                    <h4>AI 回覆內容</h4>
                    <p id="response-text"></p>
                </div>
            </div>

            <div class="modal-footer">
                <button class="btn-nav-prev" onclick="prevScreenshot()">← 上一個</button>
                <span id="screenshot-counter" class="screenshot-counter"></span>
                <button class="btn-nav-next" onclick="nextScreenshot()">下一個 →</button>
            </div>
        </div>
    `;

    document.body.appendChild(modal);

    // Add styles
    const style = document.createElement('style');
    style.textContent = `
        .screenshot-modal {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            z-index: 10000;
        }

        .screenshot-modal.active {
            display: flex;
            align-items: center;
            justify-content: center;
        }

        .modal-overlay {
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0, 0, 0, 0.8);
            cursor: pointer;
        }

        .modal-content {
            position: relative;
            background: var(--black-card);
            border: 2px solid var(--neon-green);
            border-radius: 12px;
            width: 90%;
            max-width: 900px;
            max-height: 90vh;
            overflow-y: auto;
            display: flex;
            flex-direction: column;
        }

        .modal-close {
            position: absolute;
            top: 16px;
            right: 16px;
            background: none;
            border: none;
            color: var(--text-secondary);
            font-size: 24px;
            cursor: pointer;
            z-index: 10001;
        }

        .modal-close:hover {
            color: var(--neon-green);
        }

        .modal-header {
            padding: 24px;
            border-bottom: 1px solid var(--border-color);
        }

        .modal-header h3 {
            font-size: 20px;
            font-weight: 700;
            color: var(--text-primary);
            margin: 0 0 8px 0;
        }

        .modal-platform {
            font-size: 12px;
            color: var(--neon-green);
            text-transform: uppercase;
            margin: 0;
        }

        .modal-body {
            flex: 1;
            padding: 24px;
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 24px;
        }

        .screenshot-container {
            display: flex;
            align-items: center;
            justify-content: center;
            background: #0a0a0a;
            border: 1px solid var(--border-color);
            border-radius: 8px;
            overflow: auto;
        }

        .screenshot-container img {
            max-width: 100%;
            max-height: 500px;
            border-radius: 4px;
        }

        .response-transcript {
            display: flex;
            flex-direction: column;
        }

        .response-transcript h4 {
            font-size: 14px;
            font-weight: 700;
            color: var(--neon-green);
            text-transform: uppercase;
            margin: 0 0 12px 0;
        }

        .response-transcript p {
            font-size: 13px;
            color: var(--text-secondary);
            line-height: 1.6;
            margin: 0;
            overflow-y: auto;
            max-height: 400px;
            padding-right: 12px;
        }

        .modal-footer {
            padding: 16px 24px;
            border-top: 1px solid var(--border-color);
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 16px;
        }

        .btn-nav-prev, .btn-nav-next {
            padding: 8px 16px;
            background: transparent;
            border: 1px solid var(--border-color);
            color: var(--text-secondary);
            border-radius: 6px;
            cursor: pointer;
            font-size: 12px;
            font-weight: 600;
            transition: all 0.2s;
        }

        .btn-nav-prev:hover, .btn-nav-next:hover {
            border-color: var(--neon-green);
            color: var(--neon-green);
        }

        .screenshot-counter {
            font-size: 12px;
            color: var(--text-tertiary);
            min-width: 80px;
            text-align: center;
        }

        @media (max-width: 768px) {
            .modal-body {
                grid-template-columns: 1fr;
            }
        }
    `;
    document.head.appendChild(style);
}

function openScreenshotViewer(platform, screenshots, startIndex = 0) {
    window.currentScreenshots = screenshots;
    window.currentScreenshotIndex = startIndex;
    window.currentPlatform = platform;
    updateScreenshotDisplay();
    document.getElementById('screenshot-modal').classList.add('active');
}

function closeScreenshotModal() {
    document.getElementById('screenshot-modal').classList.remove('active');
}

function updateScreenshotDisplay() {
    const idx = window.currentScreenshotIndex || 0;
    const screenshots = window.currentScreenshots || [];

    if (screenshots.length === 0) return;

    const current = screenshots[idx];
    document.getElementById('screenshot-title').textContent = current.query || 'Query';
    document.getElementById('screenshot-platform').textContent = window.currentPlatform;
    document.getElementById('screenshot-image').src = current.screenshot_url || '';
    document.getElementById('response-text').textContent = current.response_text || '';
    document.getElementById('screenshot-counter').textContent = `${idx + 1} / ${screenshots.length}`;
}

function prevScreenshot() {
    if (!window.currentScreenshots) return;
    window.currentScreenshotIndex = Math.max(0, (window.currentScreenshotIndex || 0) - 1);
    updateScreenshotDisplay();
}

function nextScreenshot() {
    if (!window.currentScreenshots) return;
    window.currentScreenshotIndex = Math.min(
        window.currentScreenshots.length - 1,
        (window.currentScreenshotIndex || 0) + 1
    );
    updateScreenshotDisplay();
}

// ============================================
// 2. PDF REPORT EXPORT
// ============================================

async function exportPDFReport() {
    // Check if jsPDF is available
    if (typeof html2pdf === 'undefined') {
        alert('PDF 庫載入中，請稍候...');
        loadPDFLibraries();
        return;
    }

    const element = document.querySelector('[data-exportable="true"]') || document.querySelector('.results-container');

    if (!element) {
        alert('找不到要匯出的內容');
        return;
    }

    const filename = `GEO-Analysis-${STATE.brand}-${new Date().toISOString().split('T')[0]}.pdf`;

    const opt = {
        margin: 10,
        filename: filename,
        image: { type: 'jpeg', quality: 0.98 },
        html2canvas: { scale: 2 },
        jsPDF: { orientation: 'portrait', unit: 'mm', format: 'a4' }
    };

    try {
        html2pdf().set(opt).from(element).save();
    } catch (err) {
        console.error('PDF 匯出失敗:', err);
        alert('PDF 匯出失敗，請重試');
    }
}

function loadPDFLibraries() {
    const html2pdfScript = document.createElement('script');
    html2pdfScript.src = 'https://cdnjs.cloudflare.com/ajax/libs/html2pdf.js/0.10.1/html2pdf.bundle.min.js';
    document.head.appendChild(html2pdfScript);
}

// ============================================
// 3. LLMREFS CITATION SOURCE INTEGRATION
// ============================================

function renderCitationSources(data) {
    if (!data || !data.ai_platforms) return '';

    const sources = data.ai_platforms.map(platform => {
        const citationBreakdown = platform.citation_sources || {};
        const total = Object.values(citationBreakdown).reduce((a, b) => a + b, 0) || 1;

        return `
            <div class="citation-platform">
                <h4>${platform.name}</h4>
                <div class="citation-breakdown">
                    ${Object.entries(citationBreakdown)
                        .sort((a, b) => b[1] - a[1])
                        .map(([source, count]) => {
                            const percent = Math.round((count / total) * 100);
                            return `
                                <div class="citation-source">
                                    <span class="source-name">${source}</span>
                                    <div class="progress-bar">
                                        <div class="progress-fill" style="width: ${percent}%"></div>
                                    </div>
                                    <span class="source-percent">${percent}%</span>
                                </div>
                            `;
                        })
                        .join('')}
                </div>
            </div>
        `;
    }).join('');

    return `
        <section class="citation-section">
            <h3>📚 引用來源分析 (LLMrefs)</h3>
            <div class="citations-grid">
                ${sources}
            </div>
        </section>
    `;
}

// ============================================
// 4. INIT & STYLES
// ============================================

function initP1Features() {
    // Initialize screenshot viewer
    initScreenshotViewer();

    // Add export button to results
    const resultsHeader = document.querySelector('.results-header');
    if (resultsHeader && !resultsHeader.querySelector('.btn-export-pdf')) {
        const exportBtn = document.createElement('button');
        exportBtn.className = 'btn-cta btn-cta-secondary btn-export-pdf';
        exportBtn.textContent = '📄 匯出 PDF 報告';
        exportBtn.onclick = exportPDFReport;
        resultsHeader.appendChild(exportBtn);
    }

    // Add PDF button styles
    const style = document.createElement('style');
    style.textContent = `
        .btn-export-pdf {
            margin-left: auto;
        }

        .citation-section {
            margin-top: 32px;
            padding-top: 32px;
            border-top: 2px solid var(--border-color);
        }

        .citation-section h3 {
            font-size: 16px;
            font-weight: 700;
            color: var(--neon-green);
            text-transform: uppercase;
            margin: 0 0 20px 0;
        }

        .citations-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
        }

        .citation-platform {
            background: var(--black-hover);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            padding: 16px;
        }

        .citation-platform h4 {
            font-size: 14px;
            font-weight: 600;
            color: var(--text-primary);
            margin: 0 0 12px 0;
        }

        .citation-breakdown {
            display: flex;
            flex-direction: column;
            gap: 8px;
        }

        .citation-source {
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 12px;
        }

        .source-name {
            color: var(--text-secondary);
            width: 100px;
            flex-shrink: 0;
        }

        .progress-bar {
            flex: 1;
            height: 6px;
            background: rgba(145, 213, 0, 0.1);
            border-radius: 3px;
            overflow: hidden;
        }

        .progress-fill {
            height: 100%;
            background: linear-gradient(90deg, var(--neon-green), var(--neon-bright));
            transition: width 0.3s ease;
        }

        .source-percent {
            color: var(--text-tertiary);
            width: 40px;
            text-align: right;
            flex-shrink: 0;
        }
    `;
    document.head.appendChild(style);
}

// Auto-init when DOM ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initP1Features);
} else {
    initP1Features();
}
