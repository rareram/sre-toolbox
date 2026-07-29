import { Injectable } from '@angular/core'
import { AppService, ConfigService, NotificationsService, PlatformService, TranslateService } from 'tabby-core'
import { BaseTerminalTabComponent } from 'tabby-terminal'
import { Subject, Subscription } from 'rxjs'
import * as fs from 'fs'
import * as path from 'path'
import * as os from 'os'
import { execFile } from 'child_process'
import { detectAsciinemaCLI } from './cliDetector'
import { registerPluginTranslations, translations } from '../i18n'

export interface AsciinemaHeader {
    version: number
    width: number
    height: number
    timestamp: number
    title?: string
    env?: Record<string, string>
    idle_time_limit?: number
}

export interface RecordingSession {
    tab: BaseTerminalTabComponent<any>
    startTime: number
    events: Array<[number, string, string]>
    header: AsciinemaHeader
    subscriptionOutput?: Subscription
    subscriptionResize?: Subscription
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
        this.app.tabsChanged$.subscribe(() => {
            for (const [tab] of Array.from(this.activeRecordings.entries())) {
                if (!this.app.tabs.includes(tab as any)) {
                    this.stopRecording(tab)
                }
            }
        })
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
        return this.config.store.pluginConfig?.['asciinema']?.filenamePattern || '{host}_{date}'
    }

    get recordingTitle (): string {
        return this.config.store.pluginConfig?.['asciinema']?.recordingTitle || 'Tabby Session Recording'
    }

    get idleTimeLimit (): number {
        const val = Number(this.config.store.pluginConfig?.['asciinema']?.idleTimeLimit)
        return isNaN(val) ? 2.0 : val
    }

    get maskingKeywords (): string {
        return this.config.store.pluginConfig?.['asciinema']?.maskingKeywords || ''
    }

    isRecording (tab: BaseTerminalTabComponent<any>): boolean {
        return this.activeRecordings.has(tab)
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
        if (!tab || !tab.session) {
            this.notifications.error(this.translate.instant('Recording Error'), this.translate.instant('No active terminal session.'))
            return
        }

        const cmd = `asciinema play "${this.lastRecordedFilePath}"\r`
        tab.session.write(Buffer.from(cmd) as any)
        this.notifications.info(this.translate.instant('Asciinema Playback Started'), `asciinema play "${this.lastRecordedFilePath}"`)
    }

    openSettings (): void {
        this.app.openNewTab({ type: 'settings', activeTab: 'asciinema' } as any)
    }

    startRecording (tab: BaseTerminalTabComponent<any>): void {
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

        const verNumber = this.formatVersion === 'v3' ? 3 : 2
        const headerTitle = this.recordingTitle && this.recordingTitle.trim() ? this.recordingTitle.trim() : (tab.title || 'Tabby Session Recording')

        const header: AsciinemaHeader = {
            version: verNumber,
            width: columns,
            height: rows,
            timestamp: Math.floor(now),
            title: headerTitle,
            env: {
                TERM: 'xterm-256color',
            },
        }

        if (this.idleTimeLimit > 0) {
            header.idle_time_limit = this.idleTimeLimit
        }

        const session: RecordingSession = {
            tab,
            startTime: now,
            events: [],
            header,
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

        this.activeRecordings.set(tab, session)
        this.stateChanged$.next()
        this.notifications.notice(this.translate.instant('Asciinema recording started.'))
    }

    async stopRecording (tab: BaseTerminalTabComponent<any>): Promise<void> {
        const session = this.activeRecordings.get(tab)
        if (!session) {
            return
        }

        // Unsubscribe
        session.subscriptionOutput?.unsubscribe()
        session.subscriptionResize?.unsubscribe()
        this.activeRecordings.delete(tab)
        this.stateChanged$.next()

        // Save cast file
        try {
            const outputDir = this.saveDir
            if (!fs.existsSync(outputDir)) {
                fs.mkdirSync(outputDir, { recursive: true })
            }

            const rawHost = (tab as any)?.profile?.options?.host || tab.title || 'local'
            const hostSanitized = rawHost.replace(/[/\\?%*:|"<> ]/g, '-').replace(/-+/g, '-').replace(/^-|-$/g, '') || 'session'
            const dateStr = new Date().toISOString().replace(/T/, '-').replace(/[:.]/g, '').slice(0, 15)
            const prefixStr = (this.filePrefix && this.filePrefix.trim() ? this.filePrefix.trim() : 'asciinema').replace(/[/\\?%*:|"<> ]/g, '-')
            const titleStr = (this.recordingTitle && this.recordingTitle.trim() ? this.recordingTitle.trim() : 'session').replace(/[/\\?%*:|"<> ]/g, '-')

            let pattern = this.filenamePattern || '{host}_{date}'
            pattern = pattern
                .replace(/\{host\}|\%host\%/g, hostSanitized)
                .replace(/\{date\}|\%date\%/g, dateStr)
                .replace(/\{prefix\}|\%prefix\%/g, prefixStr)
                .replace(/\{title\}|\%title\%/g, titleStr)
                .replace(/[/\\?%*:|"<> ]/g, '-')
                .replace(/-+/g, '-')

            let baseFilename = pattern.replace(/\.cast$/i, '')
            if (!baseFilename || baseFilename === '-') {
                baseFilename = `${prefixStr}_${dateStr}`
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

            // 마스킹 키워드 준비
            const keywords = this.maskingKeywords
                .split(',')
                .map(k => k.trim())
                .filter(k => k.length > 0)

            for (const event of session.events) {
                const time = Math.round(event[0] * 10000) / 10000
                let text = event[2]
                if (keywords.length > 0 && event[1] === 'o') {
                    for (const kw of keywords) {
                        if (kw) {
                            const escaped = kw.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
                            text = text.replace(new RegExp(escaped, 'g'), '***')
                        }
                    }
                }
                lines.push(JSON.stringify([time, event[1], text]))
            }

            fs.writeFileSync(filePath, lines.join('\n') + '\n', 'utf8')
            this.lastRecordedFilePath = filePath

            // Copy path to clipboard
            this.platform.setClipboard({ text: filePath })

            // CLI Detection & Guide Notice
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
        } catch (err: any) {
            this.notifications.error(this.translate.instant('Save Failed'), err?.message || String(err))
        }
    }

    uploadToAsciinema(filePath: string): Promise<string> {
        return new Promise((resolve, reject) => {
            if (!fs.existsSync(filePath)) {
                reject(new Error('File not found: ' + filePath))
                return
            }

            execFile('asciinema', ['upload', filePath], (err, stdout, stderr) => {
                const combined = (stdout || '') + '\n' + (stderr || '')
                const urlMatch = combined.match(/https:\/\/asciinema\.org\/a\/[a-zA-Z0-9]+/)

                if (urlMatch) {
                    resolve(urlMatch[0])
                } else if (err) {
                    reject(new Error(err.message || combined.trim()))
                } else {
                    resolve(combined.trim())
                }
            })
        })
    }
}
