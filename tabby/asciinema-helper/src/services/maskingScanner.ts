export interface DetectedItem {
    value: string
    type: string
    count: number
    enabled: boolean
}

const REGEX_PATTERNS: Array<{ name: string; regex: RegExp }> = [
    {
        name: 'IP Address',
        regex: /\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b/g,
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
    {
        name: 'Email Address',
        regex: /\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b/g,
    },
]

export function scanSensitiveData(content: string): DetectedItem[] {
    const itemMap = new Map<string, { type: string; count: number }>()

    for (const pattern of REGEX_PATTERNS) {
        pattern.regex.lastIndex = 0
        let match: RegExpExecArray | null

        while ((match = pattern.regex.exec(content)) !== null) {
            const matchedValue = (match[1] || match[0]).trim()
            // Ignore trivial IP addresses like 127.0.0.1 or 0.0.0.0
            if (matchedValue === '127.0.0.1' || matchedValue === '0.0.0.0' || matchedValue.length < 3) {
                continue
            }

            if (itemMap.has(matchedValue)) {
                itemMap.get(matchedValue)!.count += 1
            } else {
                itemMap.set(matchedValue, { type: pattern.name, count: 1 })
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

export function maskCastContent(content: string, keywords: string[], replacement: string = '***'): string {
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
                    if (kw && kw.trim()) {
                        const escaped = kw.trim().replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
                        text = text.replace(new RegExp(escaped, 'g'), replacement)
                    }
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
            if (kw && kw.trim()) {
                const escaped = kw.trim().replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
                rawText = rawText.replace(new RegExp(escaped, 'g'), replacement)
            }
        }
        maskedLines.push(rawText)
    }

    return maskedLines.join('\n')
}
