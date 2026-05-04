/**
 * Simple Markdown → HTML renderer.
 * Handles common markdown syntax used in dataset descriptions.
 */
export function renderMarkdown(md: string): string {
  let html = md
    // Escape HTML entities first
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');

  // Code blocks (``` ... ```)
  html = html.replace(/```(\w*)\n([\s\S]*?)```/g, (_m, lang, code) => {
    return `<pre><code>${code.trim()}</code></pre>`;
  });

  // Inline code (`...`)
  html = html.replace(/`([^`]+)`/g, '<code>$1</code>');

  // Headers
  html = html.replace(/^#### (.+)$/gm, '<h4>$1</h4>');
  html = html.replace(/^### (.+)$/gm, '<h3>$1</h3>');
  html = html.replace(/^## (.+)$/gm, '<h2>$1</h2>');
  html = html.replace(/^# (.+)$/gm, '<h1>$1</h1>');

  // Bold / Italic
  html = html.replace(/\*\*\*(.+?)\*\*\*/g, '<strong><em>$1</em></strong>');
  html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
  html = html.replace(/\*(.+?)\*/g, '<em>$1</em>');

  // Links [text](url)
  html = html.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank">$1</a>');

  // Images ![alt](url)
  html = html.replace(/!\[([^\]]*)\]\(([^)]+)\)/g, '<img src="$2" alt="$1" style="max-width:100%;">');

  // Horizontal rules
  html = html.replace(/^---+$/gm, '<hr>');

  // Blockquotes
  html = html.replace(/^&gt; (.+)$/gm, '<blockquote>$1</blockquote>');
  // Merge adjacent blockquotes
  html = html.replace(/<\/blockquote>\n<blockquote>/g, '\n');

  // Unordered lists
  html = html.replace(/^[\*\-] (.+)$/gm, '<li>$1</li>');
  html = html.replace(/(<li>.*<\/li>[\n]?)+/g, '<ul>$&</ul>');

  // Ordered lists
  html = html.replace(/^\d+\. (.+)$/gm, '<li>$1</li>');

  // Tables (simple: | a | b |)
  html = html.replace(/^\|(.+)\|$/gm, (_m: string, content: string) => {
    const cells = content.split('|').map(c => c.trim());
    if (cells.every(c => /^[-:]+$/.test(c))) return ''; // skip separator row
    const tag = 'td';
    return '<tr>' + cells.map(c => `<${tag}>${c}</${tag}>`).join('') + '</tr>';
  });
  // Wrap adjacent <tr> groups in <table>
  html = html.replace(/(<tr>.*<\/tr>[\n]?){2,}/g, '<table>$&</table>');

  // Paragraphs: wrap lines that aren't already HTML tags
  html = html.replace(/^(?!<[a-z]|$)(.+)$/gm, '<p>$1</p>');

  // Clean up empty paragraphs and double-wrapping
  html = html.replace(/<p><\/(h[1-4]|ul|ol|table|pre|blockquote|hr)>/g, '</$1>');
  html = html.replace(/<(h[1-4]|ul|ol|table|pre|blockquote)><\/p>/g, '<$1>');
  html = html.replace(/<p><(h[1-4]|ul|ol|table|pre|blockquote)/g, '<$1');
  html = html.replace(/<\/(h[1-4]|ul|ol|table|pre|blockquote)><\/p>/g, '</$1>');
  html = html.replace(/<p>\s*<\/p>/g, '');

  return html;
}
