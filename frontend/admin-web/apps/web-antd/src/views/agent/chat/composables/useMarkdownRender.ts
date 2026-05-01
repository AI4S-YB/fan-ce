import MarkdownIt from 'markdown-it'
import hljs from 'highlight.js'
import { h } from 'vue'

const DISALLOWED_TAGS = ['script', 'style', 'iframe', 'object', 'embed', 'link']

function sanitizeHtml(input: string): string {
  if (typeof window === 'undefined') {
    return input
  }

  const parser = new DOMParser()
  const doc = parser.parseFromString(input, 'text/html')

  DISALLOWED_TAGS.forEach((tag) => {
    doc.querySelectorAll(tag).forEach((node) => node.remove())
  })

  doc.body.querySelectorAll<HTMLElement>('*').forEach((element) => {
    Array.from(element.attributes).forEach((attr) => {
      if (attr.name.startsWith('on') || attr.value.includes('javascript:')) {
        element.removeAttribute(attr.name)
      }
    })
  })

  return doc.body.innerHTML
}

function createMarkdownRenderer() {
  return new MarkdownIt({
    html: true,
    linkify: true,
    typographer: true,
    highlight(code, language) {
      if (language && hljs.getLanguage(language)) {
        try {
          return hljs.highlight(code, { language }).value
        } catch (error) {
          console.warn('[markdown] highlight failed:', error)
        }
      }

      try {
        return hljs.highlightAuto(code).value
      } catch (error) {
        console.warn('[markdown] auto highlight failed:', error)
      }

      return code
    },
  })
}

const markdown = createMarkdownRenderer()

export function useMarkdownRender() {
  const renderToHtml = (content: string) => {
    if (!content) {
      return ''
    }

    const rawHtml = markdown.render(content)
    return sanitizeHtml(rawHtml)
  }

  const messageRender = (content: string) =>
    h('div', {
      class: 'chat-message__markdown',
      innerHTML: renderToHtml(content),
    })

  return {
    markdown,
    renderToHtml,
    messageRender,
  }
}
