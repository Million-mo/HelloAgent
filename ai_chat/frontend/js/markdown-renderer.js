// Markdown 渲染配置
export class MarkdownRenderer {
    constructor() {
        this.md = null;
        this.init();
    }

    init() {
        if (typeof markdownit !== 'undefined') {
            this.md = markdownit({
                html: true,
                linkify: true,
                typographer: true,
                breaks: true,
                highlight: (code, lang) => this.highlight(code, lang)
            });
        }
    }

    highlight(code, lang) {
        let highlighted = '';
        if (window.hljs && lang && hljs.getLanguage(lang)) {
            highlighted = hljs.highlight(code, { language: lang, ignoreIllegals: true }).value;
            if (highlighted.endsWith('\n')) {
                highlighted = highlighted.slice(0, -1);
            }
        } else if (window.hljs) {
            highlighted = hljs.highlightAuto(code).value;
        } else {
            highlighted = this.escapeHtml(code);
        }
        
        const rawLines = highlighted.split('\n');
        
        const linesHtml = rawLines.map((lineHtml, idx) => {
            const lineContent = lineHtml || '&#8203;';
            const trimmedLineContent = lineContent.replace(/\s+$/, '');
            return `<div class="line"><span class="line-number">${idx + 1}</span><span class="line-content">${trimmedLineContent}</span></div>`;
        }).join('');
        
        const langLabel = (lang || 'plaintext').toUpperCase();
        
        return `<div class="code-wrapper">
                    <div class="code-header">
                        <span class="code-lang">${langLabel}</span>
                        <button class="copy-btn" data-lang="${langLabel}">
                            <i class="fas fa-copy"></i> <i>复制</i>
                        </button>
                    </div>
                    <div class="code-body">
                        <pre><code class="hljs language-${lang || ''}">${linesHtml}</code></pre>
                    </div>
                </div>`;
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    render(content) {
        if (this.md) {
            return this.md.render(content);
        }
        return this.escapeHtml(content);
    }
}
