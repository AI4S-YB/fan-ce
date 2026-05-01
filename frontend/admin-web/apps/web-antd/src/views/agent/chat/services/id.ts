export function createTimestampedId(): string {
  const timestamp = Date.now()

  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return `${timestamp}-${crypto.randomUUID()}`
  }

  const template = 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'
  const uuid = template.replace(/[xy]/g, (char) => {
    const rand = (Math.random() * 16) | 0
    const value = char === 'x' ? rand : (rand & 0x3) | 0x8
    return value.toString(16)
  })

  return `${timestamp}-${uuid}`
}
