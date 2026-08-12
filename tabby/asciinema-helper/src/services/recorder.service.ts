import { Injectable } from '@angular/core'
import { AppService, ConfigService, NotificationsService, PlatformService, TranslateService } from 'tabby-core'
import { BaseTerminalTabComponent } from 'tabby-terminal'
import { Subject, Subscription } from 'rxjs'
import * as fs from 'fs'
import * as path from 'path'
import * as os from 'os'
import { execFile } from 'child_process'
import { detectAsciinemaCLI } from './cliDetector'
import { generateMaskReplacement, replacePreservingAnsi } from './maskingScanner'
import { registerPluginTranslations } from '../i18n'

export interface AsciinemaHeader {
    version: number
    width?: number
    height?: number
    term?: { cols: number; rows: number }
    timestamp: number
    title?: string
    env?: Record<string, string>
    idle_time_limit?: number
}

export interface RecordingOptions {
    customFileLimitMB?: number
    customMaxSplits?: number
}

export interface RecordingSession {
    tab: BaseTerminalTabComponent<any>
    startTime: number
    events: Array<[number, string, string]>
    header: AsciinemaHeader
    customPrefix?: string
    customFileLimitMB?: number
    customMaxSplits?: number
    subscriptionOutput?: Subscription
    subscriptionResize?: Subscription
    subscriptionDestroyed?: Subscription
    livenessTimer?: any
}

function extractCleanHost (tab: any): string {
    if (!tab) return 'local'

    if (tab.profile?.options?.host && typeof tab.profile.options.host === 'string') {
        const host = tab.profile.options.host.trim()
        if (host && !host.includes('/') && !host.includes('\\')) {
            return host
        }
    }

    let rawTitle = tab.title || tab.customTitle || 'local'
    if (typeof rawTitle !== 'string') {
        rawTitle = String(rawTitle)
    }

    if (rawTitle.includes(':')) {
        rawTitle = rawTitle.split(':')[0]
    }
    if (rawTitle.includes('~')) {
        rawTitle = rawTitle.split('~')[0]
    }
    if (rawTitle.includes(' - ')) {
        rawTitle = rawTitle.split(' - ')[0]
    }

    const parts = rawTitle.trim().split(/[\s/\\]+/)
    const clean = parts[0] ? parts[0].trim() : 'local'
    return clean || 'local'
}

@Injectable({ providedIn: 'root' })
export class AsciinemaRecorderService {
    readonly stateChanged$ = new Subject<void>()
    private activeRecordings = new Map<BaseTerminalTabComponent<any>, RecordingSession>()
    public lastRecordedFilePath: string | null = null

    constructor (
        private app: AppService,
        private config: ConfigService,
        private notifications: NotificationsService,
        private platform: PlatformService,
        private translate: TranslateService,
    ) {
        registerPluginTranslations(this.translate)

        // Application shutdown shield: Safety flush when Tabby application quits
        if (typeof window !== 'undefined') {
            window.addEventListener('beforeunload', () => {
                for (const [tab] of Array.from(this.activeRecordings.entries())) {
                    this.stopRecording(tab)
                }
            })
        }
    }

    get saveDir (): string {
        const configured = this.config.store.pluginConfig?.['asciinema']?.savePath
        return configured && configured.trim() ? configured : path.join(os.homedir(), 'Downloads', 'AsciinemaRecordings')
    }

    get formatVersion (): string {
        return this.config.store.pluginConfig?.['asciinema']?.formatVersion || 'v2'
    }

    get filePrefix (): string {
        return this.config.store.pluginConfig?.['asciinema']?.filePrefix || 'asciinema'
    }

    get filenamePattern (): string {
        const pattern = this.config.store.pluginConfig?.['asciinema']?.filenamePattern
        if (!pattern || pattern === '{host}_{date}') {
            // Auto migrate old pattern to date first
            return '{date}_{host}'
        }
        return pattern
    }

    get recordingTitle (): string {
        return this.config.store.pluginConfig?.['asciinema']?.recordingTitle || 'Tabby Session Recording'
    }

    get idleTimeLimit (): number {
        const val = Number(this.config.store.pluginConfig?.['asciinema']?.idleTimeLimit)
        return isNaN(val) ? 2.0 : val
    }

    get maxSingleFileSizeMB (): number {
        const val = Number(this.config.store.pluginConfig?.['asciinema']?.maxSingleFileSizeMB)
        return isNaN(val) || val <= 0 ? 8 : Math.min(val, 30)
    }

    get enableFileSplitting (): boolean {
        const val = this.config.store.pluginConfig?.['asciinema']?.enableFileSplitting
        return val !== undefined ? Boolean(val) : true
    }

    get maxSplitCount (): number {
        const val = Number(this.config.store.pluginConfig?.['asciinema']?.maxSplitCount)
        return isNaN(val) || val < 0 ? 0 : val
    }

    get maxStorageMB (): number {
        const val = Number(this.config.store.pluginConfig?.['asciinema']?.maxStorageMB)
        return isNaN(val) || val <= 0 ? 100 : val
    }

    get savePath (): string {
        return this.config.store.pluginConfig?.['asciinema']?.savePath || path.join(os.homedir(), 'Downloads', 'AsciinemaRecordings')
    }

    get maskingKeywords (): string {
        return this.config.store.pluginConfig?.['asciinema']?.maskingKeywords || ''
    }

    get maskingChar (): string {
        return this.config.store.pluginConfig?.['asciinema']?.maskingChar || '*'
    }

    isRecording (tab: BaseTerminalTabComponent<any>): boolean {
        return this.activeRecordings.has(tab)
    }

    getRecordingCurrentSizeMB (tab: BaseTerminalTabComponent<any>): string {
        const session = this.activeRecordings.get(tab)
        if (!session) {
            return '0.00'
        }
        const headerStr = JSON.stringify(session.header)
        const headerBytes = Buffer.byteLength(headerStr, 'utf8') + 1
        const eventBytes = session.events.reduce((acc, ev) => acc + Buffer.byteLength(ev[2], 'utf8') + 20, 0)
        const totalBytes = headerBytes + eventBytes
        return (totalBytes / (1024 * 1024)).toFixed(2)
    }

    toggleRecording (tab: BaseTerminalTabComponent<any>): void {
        if (this.isRecording(tab)) {
            this.stopRecording(tab)
        } else {
            this.startRecording(tab)
        }
    }

    playLastRecording (tab?: BaseTerminalTabComponent<any> | null): void {
        if (!this.lastRecordedFilePath) {
            this.notifications.notice(this.translate.instant('No recent .cast recording file found.'))
            return
        }

        const activeTab = tab || this.app.activeTab
        if (activeTab && (activeTab as any).session) {
            const playCmd = `asciinema play "${this.lastRecordedFilePath}"\n`
            ;(activeTab as any).session.write(playCmd)
            this.notifications.info(
                this.translate.instant('Asciinema Playback Started'),
                `$ asciinema play "${this.lastRecordedFilePath}"`,
            )
        } else {
            this.platform.setClipboard({ text: `asciinema play "${this.lastRecordedFilePath}"` })
            this.notifications.info(
                this.translate.instant('Copied to clipboard.'),
                `asciinema play "${this.lastRecordedFilePath}"`,
            )
        }
    }

    openSettings (): void {
        this.app.openNewTab({ type: 'settings', activeTab: 'asciinema' } as any)
    }

    startRecording (tab: BaseTerminalTabComponent<any>, customPrefix?: string, options?: RecordingOptions): void {
        if (this.isRecording(tab)) {
            return
        }

        if (!tab.session) {
            this.notifications.error(this.translate.instant('Recording Error'), this.translate.instant('No active terminal session.'))
            return
        }

        const columns = tab.size?.columns || 80
        const rows = tab.size?.rows || 24
        const now = Date.now() / 1000

        const isV3 = this.formatVersion === 'v3'
        const headerTitle = this.recordingTitle && this.recordingTitle.trim() ? this.recordingTitle.trim() : (tab.title || 'Tabby Session Recording')

        const header: AsciinemaHeader = {
            version: isV3 ? 3 : 2,
            timestamp: Math.floor(now),
            title: headerTitle,
            env: {
                TERM: 'xterm-256color',
            },
        }

        if (isV3) {
            header.term = { cols: columns, rows: rows }
        } else {
            header.width = columns
            header.height = rows
        }

        if (this.idleTimeLimit > 0) {
            header.idle_time_limit = this.idleTimeLimit
        }

        const session: RecordingSession = {
            tab,
            startTime: now,
            events: [],
            header,
            customPrefix,
            customFileLimitMB: options?.customFileLimitMB,
            customMaxSplits: options?.customMaxSplits,
        }

        // 1. Output stream capture
        if (tab.session.output$) {
            session.subscriptionOutput = tab.session.output$.subscribe((data: string) => {
                const elapsedTime = (Date.now() / 1000) - session.startTime
                session.events.push([elapsedTime, 'o', data])
            })
        }

        // 2. Resize stream capture
        if (tab.frontend?.resize$) {
            session.subscriptionResize = tab.frontend.resize$.subscribe(({ columns: c, rows: r }: { columns: number, rows: number }) => {
                const elapsedTime = (Date.now() / 1000) - session.startTime
                session.events.push([elapsedTime, 'r', `${c}x${r}`])
            })
        }

        // 3. Tab destroyed$ stream capture for safe auto-flush when tab closes
        if ((tab as any).destroyed$) {
            session.subscriptionDestroyed = (tab as any).destroyed$.subscribe(() => {
                this.stopRecording(tab)
            })
        }

        // 4. Periodic 10-second Liveness & Size Status Notification
        session.livenessTimer = setInterval(() => {
            if (this.isRecording(tab)) {
                const curSize = this.getRecordingCurrentSizeMB(tab)
                const hostName = (session.customPrefix && session.customPrefix.trim()) ? session.customPrefix.trim() : extractCleanHost(tab)
                this.notifications.notice(
                    `${this.translate.instant('Asciinema Recording Active')} [${hostName}] - ${curSize} MB / ${this.maxSingleFileSizeMB} MB`
                )
            }
        }, 10000)

        this.activeRecordings.set(tab, session)
        this.stateChanged$.next()
        this.notifications.notice(this.translate.instant('Asciinema recording started.'))
    }

    async stopRecording (tab: BaseTerminalTabComponent<any>): Promise<void> {
        const session = this.activeRecordings.get(tab)
        if (!session) {
            return
        }

        // Unsubscribe & clear liveness timer
        session.subscriptionOutput?.unsubscribe()
        session.subscriptionResize?.unsubscribe()
        session.subscriptionDestroyed?.unsubscribe()
        if (session.livenessTimer) {
            clearInterval(session.livenessTimer)
            session.livenessTimer = null
        }

        this.activeRecordings.delete(tab)
        this.stateChanged$.next()

        // Save cast file
        try {
            const outputDir = this.saveDir
            if (!fs.existsSync(outputDir)) {
                fs.mkdirSync(outputDir, { recursive: true })
            }

            const rawHost = (session.customPrefix && session.customPrefix.trim()) ? session.customPrefix.trim() : extractCleanHost(tab)
            const hostSanitized = rawHost.replace(/[/\\?%*:|"<> ]/g, '-').replace(/-+/g, '-').replace(/^-|-$/g, '') || 'session'
            const dateStr = new Date().toISOString().replace(/T/, '-').replace(/[:.]/g, '').slice(0, 15)
            const prefixStr = (this.filePrefix && this.filePrefix.trim() ? this.filePrefix.trim() : 'asciinema').replace(/[/\\?%*:|"<> ]/g, '-')
            const titleStr = (this.recordingTitle && this.recordingTitle.trim() ? this.recordingTitle.trim() : 'session').replace(/[/\\?%*:|"<> ]/g, '-')

            let pattern = this.filenamePattern
            if (!pattern || pattern === '{host}_{date}') {
                pattern = '{date}_{host}'
            }

            pattern = pattern
                .replace(/\{host\}|\[host\]|\%host\%/g, hostSanitized)
                .replace(/\{date\}|\[date\]|\%date\%/g, dateStr)
                .replace(/\{prefix\}|\[prefix\]|\%prefix\%/g, prefixStr)
                .replace(/\{title\}|\[title\]|\%title\%/g, titleStr)
                .replace(/[/\\?%*:|"<> ]/g, '-')
                .replace(/-+/g, '-')

            let baseFilename = pattern.replace(/\.cast$/i, '')
            if (!baseFilename || baseFilename === '-') {
                baseFilename = `${dateStr}_${hostSanitized}`
            }

            let filename = `${baseFilename}.cast`
            let filePath = path.join(outputDir, filename)

            // 중복 방지 방어벽 (Filename Collision Shield)
            let counter = 1
            while (fs.existsSync(filePath)) {
                filename = `${baseFilename}_${counter}.cast`
                filePath = path.join(outputDir, filename)
                counter++
            }

            const lines: string[] = []
            lines.push(JSON.stringify(session.header))

            // 마스킹 키워드 및 마스킹 문자 준비
            const keywords = this.maskingKeywords
                .split(',')
                .map(k => k.trim())
                .filter(k => k.length > 0)

            const maskChar = this.maskingChar || '*'

            const eventLines: string[] = []
            for (const event of session.events) {
                const time = Math.round(event[0] * 10000) / 10000
                let text = event[2]
                if (keywords.length > 0 && event[1] === 'o') {
                    for (const kw of keywords) {
                        if (kw) {
                            text = replacePreservingAnsi(text, kw, maskChar)
                        }
                    }
                }
                eventLines.push(JSON.stringify([time, event[1], text]))
            }

            const headerStr = JSON.stringify(session.header)
            const effectiveMaxMB = (session.customFileLimitMB && session.customFileLimitMB > 0) ? session.customFileLimitMB : this.maxSingleFileSizeMB
            const effectiveMaxSplits = (session.customMaxSplits !== undefined && session.customMaxSplits >= 0) ? session.customMaxSplits : this.maxSplitCount

            const maxBytes = effectiveMaxMB * 1024 * 1024
            const totalBytes = Buffer.byteLength(headerStr, 'utf8') + eventLines.reduce((acc, line) => acc + Buffer.byteLength(line, 'utf8') + 1, 0)

            if (totalBytes > maxBytes && this.enableFileSplitting) {
                let partIndex = 1
                let currentLines: string[] = [headerStr]
                let currentBytes = Buffer.byteLength(headerStr, 'utf8') + 1
                const savedFiles: string[] = []
                const limit = effectiveMaxSplits

                for (const eline of eventLines) {
                    const lineBytes = Buffer.byteLength(eline, 'utf8') + 1
                    if (currentLines.length > 1 && (currentBytes + lineBytes) > maxBytes) {
                        if (limit > 0 && partIndex >= limit) {
                            // 01 / 11 케이스: Split 개수 제한 도달 시 즉시 분할 중단 (Stop)
                            break
                        }
                        let suffix = partIndex === 1 ? '' : `_${partIndex}`
                        let partFilePath = path.join(outputDir, `${baseFilename}${suffix}.cast`)
                        let splitCounter = 1
                        while (fs.existsSync(partFilePath)) {
                            suffix = partIndex === 1 ? `_${splitCounter}` : `_${partIndex}_${splitCounter}`
                            partFilePath = path.join(outputDir, `${baseFilename}${suffix}.cast`)
                            splitCounter++
                        }
                        fs.writeFileSync(partFilePath, currentLines.join('\n') + '\n', 'utf8')
                        savedFiles.push(partFilePath)
                        this.cleanupOldRecordings(outputDir)

                        partIndex++
                        currentLines = [headerStr, eline]
                        currentBytes = Buffer.byteLength(headerStr, 'utf8') + 1 + lineBytes
                    } else {
                        currentLines.push(eline)
                        currentBytes += lineBytes
                    }
                }

                if (currentLines.length > 1 && (limit === 0 || partIndex <= limit)) {
                    let suffix = partIndex === 1 ? '' : `_${partIndex}`
                    let partFilePath = path.join(outputDir, `${baseFilename}${suffix}.cast`)
                    let splitCounter = 1
                    while (fs.existsSync(partFilePath)) {
                        suffix = partIndex === 1 ? `_${splitCounter}` : `_${partIndex}_${splitCounter}`
                        partFilePath = path.join(outputDir, `${baseFilename}${suffix}.cast`)
                        splitCounter++
                    }
                    fs.writeFileSync(partFilePath, currentLines.join('\n') + '\n', 'utf8')
                    savedFiles.push(partFilePath)
                    this.cleanupOldRecordings(outputDir)
                }

                this.lastRecordedFilePath = savedFiles[0] || filePath
                this.platform.setClipboard({ text: savedFiles[0] || filePath })

                const title = this.translate.instant('Asciinema recording finished & saved')
                const limitNote = limit > 0 && partIndex >= limit ? `\n(${this.translate.instant('Reached max split limit')}: ${limit})` : ''
                this.notifications.info(
                    title,
                    `${this.translate.instant('Save Path:')}\n${savedFiles[0]} (+${savedFiles.length - 1} split parts)${limitNote}\n\n$ asciinema play "${savedFiles[0]}"`,
                )
                return
            }

            // Standard Single File Save
            const fullContent = [headerStr, ...eventLines].join('\n') + '\n'
            fs.writeFileSync(filePath, fullContent, 'utf8')
            this.lastRecordedFilePath = filePath

            this.cleanupOldRecordings(outputDir)
            this.platform.setClipboard({ text: filePath })

            const cli = await detectAsciinemaCLI()
            const title = this.translate.instant('Asciinema recording finished & saved')
            const saveLabel = this.translate.instant('Save Path:')
            const cmdLabel = this.translate.instant('CLI Playback Command:')
            const guideLabel = this.translate.instant('CLI Install Guide')

            if (cli.installed) {
                this.notifications.info(
                    title,
                    `${saveLabel}\n${filePath}\n\n${cmdLabel}\n$ asciinema play "${filePath}"`,
                )
            } else {
                this.notifications.info(
                    title,
                    `${saveLabel}\n${filePath}\n\n${guideLabel} (${cli.platformName}): $ ${cli.guide}`,
                )
            }
        } catch (e: any) {
            this.notifications.error(this.translate.instant('Save Failed'), e.message || String(e))
        }
    }

    async uploadToAsciinema (filePath: string): Promise<string> {
        if (!fs.existsSync(filePath)) {
            throw new Error(`File not found: ${filePath}`)
        }

        const cli = await detectAsciinemaCLI()
        let binPath = 'asciinema'
        if (cli.installed && cli.guide.includes('brew')) {
            if (fs.existsSync('/opt/homebrew/bin/asciinema')) {
                binPath = '/opt/homebrew/bin/asciinema'
            } else if (fs.existsSync('/usr/local/bin/asciinema')) {
                binPath = '/usr/local/bin/asciinema'
            }
        }

        return new Promise((resolve, reject) => {
            const envPATH = process.env.PATH || ''
            const extraPaths = '/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:~/.local/bin'
            const fullPATH = `${extraPaths}:${envPATH}`

            execFile(binPath, ['upload', filePath], { env: { ...process.env, PATH: fullPATH } }, (err, stdout, stderr) => {
                const combined = `${stdout}\n${stderr}`
                const urlMatch = combined.match(/(https:\/\/asciinema\.org\/a\/[A-Za-z0-9]+)/)
                if (urlMatch) {
                    resolve(urlMatch[1])
                } else if (err) {
                    reject(new Error(err.message || stderr || 'Upload failed'))
                } else {
                    reject(new Error(`Could not find upload URL in CLI output:\n${combined}`))
                }
            })
        })
    }

    private cleanupOldRecordings (dirPath: string): void {
        try {
            if (!fs.existsSync(dirPath)) return
            const maxBytes = this.maxStorageMB * 1024 * 1024
            const files = fs.readdirSync(dirPath)
                .filter(f => f.endsWith('.cast'))
                .map(f => {
                    const full = path.join(dirPath, f)
                    try {
                        const stat = fs.statSync(full)
                        return { path: full, size: stat.size, mtime: stat.mtimeMs }
                    } catch (e) {
                        return null
                    }
                })
                .filter((item): item is { path: string, size: number, mtime: number } => item !== null)

            let totalBytes = files.reduce((acc, curr) => acc + curr.size, 0)
            if (totalBytes <= maxBytes) return

            files.sort((a, b) => a.mtime - b.mtime)

            for (const file of files) {
                if (totalBytes <= maxBytes) break
                try {
                    fs.unlinkSync(file.path)
                    totalBytes -= file.size
                } catch (e) {}
            }
        } catch (e) {}
    }
}
