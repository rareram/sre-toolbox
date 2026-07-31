export interface DetectedItem {
    value: string
    type: string
    count: number
    enabled: boolean
}

const REGEX_PATTERNS: Array<{ name: string; regex: RegExp }> = [
    {
        name: 'IP Address',
        regex: /\b(?:25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9]?[0-9])\.(?:25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9]?[0-9])\.(?:25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9]?[0-9])\.(?:25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9]?[0-9])\b/g,
    },
    {
        name: 'Domain / Host',
        regex: /\b[a-zA-Z0-9-]+\.[a-zA-Z0-9-]+\.[a-zA-Z]{2,}\b/g,
    },
    {
        name: 'Email / SSH Address',
        regex: /\b([A-Za-z0-9._%+-]+)@([A-Za-z0-9.-]+\.[A-Za-z]{2,})\b/g,
    },
    {
        name: 'AWS Access Key',
        regex: /\b(AKIA[0-9A-Z]{16})\b/g,
    },
    {
        name: 'Bearer / JWT Token',
        regex: /Bearer\s+([A-Za-z0-9-_=]+\.[A-Za-z0-9-_=]+\.?[A-Za-z0-9-_.+/=]*)/g,
    },
    {
        name: 'Password / Secret Field',
        regex: /(?:password|passwd|pwd|token|secret|key|access_key|api_key)\s*[:=]\s*["']?([^\s"';]+)["']?/gi,
    },
]

export function scanSensitiveData(content: string): DetectedItem[] {
    const itemMap = new Map<string, { type: string; count: number }>()

    for (const pattern of REGEX_PATTERNS) {
        pattern.regex.lastIndex = 0
        let match: RegExpExecArray | null

        while ((match = pattern.regex.exec(content)) !== null) {
            const matchedValue = (match[1] || match[0]).trim()
            // Ignore trivial values like 127.0.0.1 or 0.0.0.0
            if (matchedValue === '127.0.0.1' || matchedValue === '0.0.0.0' || matchedValue.length < 3) {
                continue
            }

            if (itemMap.has(matchedValue)) {
                itemMap.get(matchedValue)!.count += 1
            } else {
                itemMap.set(matchedValue, { type: pattern.name, count: 1 })
            }

            // If Email / SSH Address matched, also extract user ID and host domain separately
            if (pattern.name === 'Email / SSH Address' && match[1] && match[2]) {
                const userId = match[1].trim()
                const hostName = match[2].trim()

                if (userId.length >= 3 && !['http', 'https', 'ftp', 'ssh', 'root', 'user', 'admin'].includes(userId.toLowerCase())) {
                    if (itemMap.has(userId)) {
                        itemMap.get(userId)!.count += 1
                    } else {
                        itemMap.set(userId, { type: 'User ID', count: 1 })
                    }
                }

                if (hostName.length >= 3 && hostName !== '127.0.0.1' && hostName !== 'localhost') {
                    if (itemMap.has(hostName)) {
                        itemMap.get(hostName)!.count += 1
                    } else {
                        itemMap.set(hostName, { type: 'Domain / Host', count: 1 })
                    }
                }
            }
        }
    }

    const results: DetectedItem[] = []
    itemMap.forEach((info, val) => {
        results.push({
            value: val,
            type: info.type,
            count: info.count,
            enabled: true,
        })
    })

    return results.sort((a, b) => b.count - a.count)
}

/**
 * 문자열이 터미널 화면상에서 차지하는 셀 폭(Display Width)을 계산합니다.
 * CJK(한글, 한자, 일어 등 전각) 문자는 2셀 폭, 아스키 및 반각 문자는 1셀 폭을 차지합니다.
 */
export function getTerminalWidth(str: string): number {
    let width = 0
    for (const char of str) {
        const code = char.charCodeAt(0)
        if (
            (code >= 0x1100 && code <= 0x11ff) || // 한글 자모
            (code >= 0x3130 && code <= 0x318f) || // 한글 호환 자모
            (code >= 0xac00 && code <= 0xd7a3) || // 한글 음절
            (code >= 0x4e00 && code <= 0x9fff) || // 한자 (CJK Unified Ideographs)
            (code >= 0x3400 && code <= 0x4dbf) || // CJK Extension A
            (code >= 0xf900 && code <= 0xfaff) || // CJK Compatibility Ideographs
            (code >= 0xff01 && code <= 0xff60)    // Full-width ASCII / Punctuation
        ) {
            width += 2
        } else {
            width += 1
        }
    }
    return width
}

/**
 * 대상 문자열의 터미널 디스플레이 폭에 맞춰 마스킹 replacement 문자열을 생성합니다.
 */
export function generateMaskReplacement(targetStr: string, replacementChar: string = '*'): string {
    const char = replacementChar || '*'
    const totalWidth = getTerminalWidth(targetStr)
    const charWidth = getTerminalWidth(char)
    const count = Math.max(1, Math.ceil(totalWidth / charWidth))
    return char.repeat(count)
}

/**
 * ANSI 이스케이프 코드(\x1b[...m 등)를 파괴하지 않고 보존하면서 키워드 마스킹을 수행합니다.
 */

export function replacePreservingAnsi(text: string, kw: string, replacementChar: string = '*'): string {
    if (!kw || !kw.trim()) return text

    const trimmedKw = kw.trim()
    const escapedKw = trimmedKw.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')

    // 1. Fast path: 단순 replacement 시도 (ANSI 코드가 키워드 내부에 끼어있지 않은 일반적인 경우)
    const simpleRegex = new RegExp(escapedKw, 'g')
    if (simpleRegex.test(text)) {
        const replacement = generateMaskReplacement(trimmedKw, replacementChar)
        return text.replace(simpleRegex, replacement)
    }

    // 2. Slow path: ANSI 코드가 단어 중간에 분할 끼어들어간 경우 정밀 안전 치환
    const ansiRegex = /\x1b(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])/g

    interface Token {
        isAnsi: boolean
        text: string
    }
    const tokens: Token[] = []
    let lastIndex = 0
    let match: RegExpExecArray | null

    ansiRegex.lastIndex = 0
    while ((match = ansiRegex.exec(text)) !== null) {
        if (match.index > lastIndex) {
            tokens.push({ isAnsi: false, text: text.slice(lastIndex, match.index) })
        }
        tokens.push({ isAnsi: true, text: match[0] })
        lastIndex = ansiRegex.lastIndex
    }
    if (lastIndex < text.length) {
        tokens.push({ isAnsi: false, text: text.slice(lastIndex) })
    }

    let plainText = ''
    for (let i = 0; i < tokens.length; i++) {
        if (!tokens[i].isAnsi) {
            plainText += tokens[i].text
        }
    }

    const kwRegex = new RegExp(escapedKw, 'g')
    let kwMatch: RegExpExecArray | null
    const matchesToReplace: Array<{ start: number; end: number }> = []

    while ((kwMatch = kwRegex.exec(plainText)) !== null) {
        matchesToReplace.push({
            start: kwMatch.index,
            end: kwMatch.index + kwMatch[0].length,
        })
    }

    if (matchesToReplace.length === 0) {
        return text
    }

    const shouldMask = new Array(plainText.length).fill(false)
    for (const m of matchesToReplace) {
        for (let idx = m.start; idx < m.end; idx++) {
            shouldMask[idx] = true
        }
    }

    let plainIndex = 0
    const replChar = replacementChar || '*'

    for (let i = 0; i < tokens.length; i++) {
        if (tokens[i].isAnsi) continue

        let newTokenText = ''
        const origTokenText = tokens[i].text

        for (let j = 0; j < origTokenText.length; j++) {
            if (shouldMask[plainIndex]) {
                const w = getTerminalWidth(origTokenText[j])
                newTokenText += replChar.repeat(w)
            } else {
                newTokenText += origTokenText[j]
            }
            plainIndex++
        }
        tokens[i].text = newTokenText
    }

    return tokens.map(t => t.text).join('')
}

export function maskCastContent(content: string, keywords: string[], replacementChar: string = '*'): string {
    if (!keywords || keywords.length === 0) {
        return content
    }

    const lines = content.split('\n')
    const maskedLines: string[] = []

    for (const line of lines) {
        if (!line.trim()) {
            maskedLines.push(line)
            continue
        }

        try {
            const parsed = JSON.parse(line)
            if (Array.isArray(parsed) && parsed.length >= 3 && parsed[1] === 'o' && typeof parsed[2] === 'string') {
                let text = parsed[2]
                for (const kw of keywords) {
                    text = replacePreservingAnsi(text, kw, replacementChar)
                }
                parsed[2] = text
                maskedLines.push(JSON.stringify(parsed))
                continue
            }
        } catch (e) {
            // Not a valid JSON line or header line, perform plain text replacement
        }

        let rawText = line
        for (const kw of keywords) {
            rawText = replacePreservingAnsi(rawText, kw, replacementChar)
        }
        maskedLines.push(rawText)
    }

    return maskedLines.join('\n')
}


