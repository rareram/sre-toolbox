import { Injectable } from '@angular/core'
import { AppService, ConfigService, NotificationsService, PlatformService, TranslateService } from 'tabby-core'
import { BaseTerminalTabComponent } from 'tabby-terminal'
import { Subject, Subscription } from 'rxjs'
import * as fs from 'fs'
import * as path from 'path'
import * as os from 'os'
import { detectAsciinemaCLI } from './cliDetector'
import { registerPluginTranslations } from '../i18n'

export interface AsciinemaHeader {
    version: number
    width: number
    height: number
    timestamp: number
    title?: string
    env?: Record<string, string>
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
    }

    get saveDir (): string {
        const configured = this.config.store.pluginConfig?.['asciinema']?.savePath
        if (configured && configured.trim()) {
            return configured.trim()
        }
        return path.join(os.homedir(), 'Downloads', 'AsciinemaRecordings')
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

        const header: AsciinemaHeader = {
            version: 2,
            width: columns,
            height: rows,
            timestamp: Math.floor(now),
            title: tab.title || 'Tabby Session Recording',
            env: {
                TERM: 'xterm-256color',
            },
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

            const dateStr = new Date().toISOString().replace(/[:.]/g, '-')
            const filename = `asciinema-${dateStr}.cast`
            const filePath = path.join(outputDir, filename)

            const lines: string[] = []
            lines.push(JSON.stringify(session.header))

            for (const event of session.events) {
                const time = Math.round(event[0] * 10000) / 10000
                lines.push(JSON.stringify([time, event[1], event[2]]))
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
}
