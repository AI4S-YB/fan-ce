import type { InterruptOption } from '#/views/agent/chat/types/chat'

import { $t } from '@vben/locales';

/**
 * Parse interrupt options from content string
 * Example: "请选择：1. 接受  2. 不接受" => [{label: '接受', value: '1'}, {label: '不接受', value: '2'}]
 */
export function parseInterruptOptions(content: string): InterruptOption[] {
  const options: InterruptOption[] = []
  const optionRegex = /(\d+)\.\s*([^\d\n]+?)(?=\s*\d+\.|$)/g
  let match

  while ((match = optionRegex.exec(content)) !== null) {
    const value = match[1].trim()
    const label = match[2].trim()
    if (label) {
      options.push({ label, value })
    }
  }
  return options
}

/**
 * Check if the option label indicates acceptance
 * Keywords: 接受, 同意, 确认, accept, yes, ok, 是
 */
export function isPrimaryOption(label: string): boolean {
  const normalizedLabel = label.toLowerCase().trim()
  const primaryKeywords = ['接受', '同意', $t('component.modal.okText'), 'accept', 'yes', 'ok', $t('grn.relationship.yes')]
  return primaryKeywords.some((keyword) =>
    normalizedLabel.includes(keyword.toLowerCase()),
  )
}

/**
 * Check if the option label indicates rejection
 * Keywords: 不接受, 拒绝, 取消, reject, no, cancel, 否
 */
export function isRejectOption(label: string): boolean {
  const normalizedLabel = label.toLowerCase().trim()
  const rejectKeywords = ['不接受', '拒绝', $t('platform.setting.cancelText'), 'reject', 'no', 'cancel', $t('grn.relationship.no')]
  return rejectKeywords.some((keyword) =>
    normalizedLabel.includes(keyword.toLowerCase()),
  )
}
