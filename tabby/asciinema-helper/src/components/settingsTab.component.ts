import { Component, OnInit } from '@angular/core'
import { ConfigService, NotificationsService, PlatformService, TranslateService } from 'tabby-core'
import { detectAsciinemaCLI, CLIInfo } from '../services/cliDetector'
import { registerPluginTranslations } from '../i18n'
import * as os from 'os'
import * as path from 'path'
import * as fs from 'fs'

@Component({
    selector: 'asciinema-settings-tab',
    template: `
        <h3 class="mb-3">{{ 'Asciinema Recording Settings' | translate }}</h3>

        <div class="form-line mb-4">
            <div class="header">
                <div class="title">{{ 'Icon Theme' | translate }}</div>
                <div class="description">{{ 'Theme selection for top toolbar button' | translate }}</div>
            </div>
            <div class="btn-group">
                <button 
                    class="btn d-inline-flex align-items-center gap-2" 
                    [class.btn-primary]="selectedTheme === 'red'" 
                    [class.btn-secondary]="selectedTheme !== 'red'" 
                    (click)="setTheme('red')">
                    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="18" height="18" fill="#ff4d4f">
                        <circle cx="12" cy="12" r="8"/>
                    </svg>
                    <span>{{ 'Classic Red' | translate }}</span>
                </button>
                <button 
                    class="btn d-inline-flex align-items-center gap-2" 
                    [class.btn-primary]="selectedTheme === 'neon'" 
                    [class.btn-secondary]="selectedTheme !== 'neon'" 
                    (click)="setTheme('neon')">
                    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="18" height="18" fill="#00f3ff">
                        <circle cx="12" cy="12" r="7" stroke="#ffffff" stroke-width="1.5"/>
                    </svg>
                    <span>{{ 'Neon Cyber' | translate }}</span>
                </button>
                <button 
                    class="btn d-inline-flex align-items-center gap-2" 
                    [class.btn-primary]="selectedTheme === 'camera'" 
                    [class.btn-secondary]="selectedTheme !== 'camera'" 
                    (click)="setTheme('camera')">
                    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="18" height="18" fill="#faad14">
                        <path d="M4 6.5A1.5 1.5 0 0 0 2.5 8v8A1.5 1.5 0 0 0 4 17.5h10a1.5 1.5 0 0 0 1.5-1.5V8A1.5 1.5 0 0 0 14 6.5H4zm13.5 2.25 4-2.5v11.5l-4-2.5V8.75z"/>
                        <circle cx="8" cy="12" r="2.5" fill="#ff4d4f"/>
                    </svg>
                    <span>{{ 'Retro Camera' | translate }}</span>
                </button>
            </div>
        </div>

        <div class="form-line mb-4">
            <div class="header">
                <div class="title">{{ 'Save Directory' | translate }}</div>
                <div class="description">{{ 'Default directory path for .cast recording files' | translate }}</div>
            </div>
            <div class="input-group w-50">
                <input type="text" class="form-control" [(ngModel)]="savePath" (change)="saveConfig()">
                <button class="btn btn-secondary" (click)="openFolder()">{{ 'Open Folder' | translate }}</button>
            </div>
        </div>

        <h3 class="mt-4 mb-3">{{ 'Hotkeys & Guide' | translate }}</h3>

        <div class="card p-3 mb-4 guide-card">
            <p class="guide-text small mb-3">
                {{ 'Asciinema features can be controlled using 5 hotkeys below. To change or add hotkeys, go to Tabby Settings > Hotkeys and search for Asciinema.' | translate }}
            </p>
            <table class="table table-dark table-striped align-middle small mb-0">
                <thead>
                    <tr>
                        <th style="width: 25%">{{ 'Feature' | translate }}</th>
                        <th style="width: 25%">{{ 'Default Hotkey' | translate }}</th>
                        <th style="width: 50%">{{ 'Description' | translate }}</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td><strong>{{ '(1) Start / Stop Recording (Toggle)' | translate }}</strong></td>
                        <td><span class="badge bg-primary">Ctrl + Shift + R</span></td>
                        <td>{{ 'Toggles recording state back and forth.' | translate }}</td>
                    </tr>
                    <tr>
                        <td><strong>{{ '(2) Start Recording Only' | translate }}</strong></td>
                        <td><span class="badge bg-secondary">{{ 'Unassigned (Custom)' | translate }}</span></td>
                        <td>{{ 'Starts recording for the active terminal session.' | translate }}</td>
                    </tr>
                    <tr>
                        <td><strong>{{ '(3) Stop Recording Only' | translate }}</strong></td>
                        <td><span class="badge bg-secondary">{{ 'Unassigned (Custom)' | translate }}</span></td>
                        <td>{{ 'Stops recording and saves to a .cast file.' | translate }}</td>
                    </tr>
                    <tr>
                        <td><strong>{{ '(4) Play Last Recording in CLI' | translate }}</strong></td>
                        <td><span class="badge bg-primary">Ctrl + Shift + P</span></td>
                        <td>{{ 'Auto-types asciinema play command into terminal session.' | translate }}</td>
                    </tr>
                    <tr>
                        <td><strong>{{ '(5) Open Settings & Help' | translate }}</strong></td>
                        <td><span class="badge bg-secondary">{{ 'Unassigned (Custom)' | translate }}</span></td>
                        <td>{{ 'Opens Asciinema settings tab immediately.' | translate }}</td>
                    </tr>
                </tbody>
            </table>
        </div>

        <h3 class="mt-4 mb-3">{{ 'CLI Usage & Playback Guide' | translate }}</h3>

        <div class="card p-3 mb-4 guide-card">
            <h5 class="mb-2 guide-title">{{ 'How to play recordings (.cast) in terminal (CLI)' | translate }}</h5>
            <p class="guide-text small mb-2">
                {{ 'When recording finishes, the absolute path of the .cast file is copied to clipboard. You can play it anytime in terminal using asciinema play command:' | translate }}
            </p>
            <div class="input-group w-100 mb-3">
                <span class="input-group-text font-monospace">$</span>
                <input type="text" class="form-control font-monospace" [value]="'asciinema play &quot;' + savePath + '/<file>.cast&quot;'" readonly>
                <button class="btn btn-outline-secondary" (click)="copyCommand('asciinema play &quot;' + savePath + '/&quot;')">{{ 'Copy Command Example' | translate }}</button>
            </div>
            <div class="small guide-tip">
                {{ 'Note: During asciinema play execution, you can use Space (pause/play), f (2x speed), . (step frame).' | translate }}
            </div>
        </div>

        <div class="card p-3 mb-3 guide-card" *ngIf="cliInfo">
            <div class="d-flex align-items-center mb-2">
                <span class="badge" [class.bg-success]="cliInfo.installed" [class.bg-warning]="!cliInfo.installed">
                    {{ cliInfo.installed ? ('CLI Installed' | translate) + ' (' + cliInfo.version + ')' : ('CLI Not Installed' | translate) }}
                </span>
                <span class="ms-3 guide-text">OS: {{ cliInfo.platformName }}</span>
            </div>

            <div *ngIf="!cliInfo.installed" class="mt-2">
                <p class="mb-1 guide-text small">{{ 'To play .cast recordings in terminal using asciinema play, CLI installation is required:' | translate }}</p>
                <div class="input-group w-75 mb-2">
                    <input type="text" class="form-control font-monospace" [value]="cliInfo.guide" readonly>
                    <button class="btn btn-outline-primary" (click)="copyCommand(cliInfo.guide)">{{ 'Copy Install Command' | translate }}</button>
                </div>
            </div>

            <div class="mt-2 d-flex gap-2">
                <button class="btn btn-primary btn-sm" (click)="openWeb(cliInfo.url)">{{ 'Visit asciinema.org' | translate }}</button>
                <button class="btn btn-secondary btn-sm" (click)="checkCLI()">{{ 'Refresh CLI Status' | translate }}</button>
            </div>
        </div>
    `,
    styles: [`
        :host {
            display: block;
            padding: 20px;
        }
        .form-line {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 12px 0;
            border-bottom: 1px solid var(--bs-border-color);
        }
        .form-line .title {
            font-weight: 600;
        }
        .form-line .description {
            font-size: 12px;
            color: var(--bs-body-color);
            opacity: 0.75;
        }
        .guide-card {
            background-color: var(--bs-body-bg, rgba(255, 255, 255, 0.04));
            border: 1px solid var(--bs-border-color, rgba(255, 255, 255, 0.15));
            border-radius: 6px;
        }
        .guide-title {
            color: var(--bs-body-color);
            font-weight: 600;
        }
        .guide-text {
            color: var(--bs-body-color);
            opacity: 0.9;
        }
        .guide-tip {
            color: var(--bs-body-color);
            opacity: 0.85;
            background: rgba(255, 255, 255, 0.06);
            padding: 8px 12px;
            border-radius: 4px;
            border-left: 3px solid #0d6efd;
        }
    `]
})
export class AsciinemaSettingsTabComponent implements OnInit {
    cliInfo?: CLIInfo
    selectedTheme: string = 'red'

    constructor(
        private config: ConfigService,
        private platform: PlatformService,
        private notifications: NotificationsService,
        private translate: TranslateService,
    ) {
        registerPluginTranslations(this.translate)
    }

    get savePath(): string {
        return this.config.store.pluginConfig?.['asciinema']?.savePath || path.join(os.homedir(), 'Downloads', 'AsciinemaRecordings')
    }

    set savePath(val: string) {
        const current = this.config.store.pluginConfig || {}
        this.config.store.pluginConfig = {
            ...current,
            asciinema: {
                ...(current['asciinema'] || {}),
                savePath: val,
            },
        }
    }

    async ngOnInit() {
        this.selectedTheme = this.config.store.pluginConfig?.['asciinema']?.iconTheme || 'red'
        await this.checkCLI()
    }

    setTheme(theme: string) {
        this.selectedTheme = theme
        const current = this.config.store.pluginConfig || {}
        this.config.store.pluginConfig = {
            ...current,
            asciinema: {
                ...(current['asciinema'] || {}),
                iconTheme: theme,
            },
        }
        this.config.save()
        const label = this.translate.instant(theme === 'red' ? 'Classic Red' : theme === 'neon' ? 'Neon Cyber' : 'Retro Camera')
        this.notifications.notice(`${this.translate.instant('Icon theme changed to')} ${label}`)
    }

    saveConfig() {
        this.config.save()
    }

    async checkCLI() {
        this.cliInfo = await detectAsciinemaCLI()
    }

    openFolder() {
        const targetPath = this.savePath
        try {
            if (!fs.existsSync(targetPath)) {
                fs.mkdirSync(targetPath, { recursive: true })
            }
            this.platform.openPath(targetPath)
        } catch (e: any) {
            this.notifications.error(this.translate.instant('Open Folder Failed'), e.message)
        }
    }

    copyCommand(cmd: string) {
        this.platform.setClipboard({ text: cmd })
        this.notifications.notice(this.translate.instant('Copied to clipboard.'))
    }

    openWeb(url: string) {
        this.platform.openExternal(url)
    }
}
