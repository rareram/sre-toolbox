import { Component, OnInit, ElementRef, ViewChild } from '@angular/core'
import { ConfigService, NotificationsService, PlatformService, TranslateService } from 'tabby-core'
import { detectAsciinemaCLI, CLIInfo } from '../services/cliDetector'
import { scanSensitiveData, maskCastContent, DetectedItem } from '../services/maskingScanner'
import { AsciinemaRecorderService } from '../services/recorder.service'
import { registerPluginTranslations } from '../i18n'
import * as os from 'os'
import * as path from 'path'
import * as fs from 'fs'

@Component({
    selector: 'asciinema-settings-tab',
    template: `
        <h3 class="mb-3">{{ 'Asciinema Recording Settings' | translate }}</h3>

        <div class="form-line mb-3">
            <div class="header">
                <div class="title">{{ 'Format Version' | translate }}</div>
                <div class="description">{{ 'Select asciinema file format version (v2 standard or v3 extended)' | translate }}</div>
            </div>
            <div class="w-50">
                <select class="form-select" [(ngModel)]="formatVersion" (change)="saveConfig()">
                    <option value="v2">{{ 'v2 (Standard, Recommended)' | translate }}</option>
                    <option value="v3">{{ 'v3 (Extended Metadata)' | translate }}</option>
                </select>
            </div>
        </div>

        <div class="form-line mb-3">
            <div class="header">
                <div class="title">{{ 'Filename Pattern' | translate }}</div>
                <div class="description">{{ 'Pattern template for generated .cast filenames' | translate }}</div>
                <div class="small text-info mt-1 fw-bold">
                    {{ 'Available variables' | translate }}: <code>[host]</code>, <code>[date]</code>, <code>[prefix]</code> (<code>[]</code>, <code>{{ '{}' }}</code>, <code>%%</code> {{ 'supported' | translate }})
                </div>
            </div>
            <div class="w-50">
                <input type="text" class="form-control" [(ngModel)]="filenamePattern" (change)="saveConfig()" [attr.placeholder]="'{host}_{date}'">
            </div>
        </div>

        <div class="form-line mb-3">
            <div class="header">
                <div class="title">{{ 'Default Prefix' | translate }}</div>
                <div class="description">{{ 'Fallback prefix string for prefix variable' | translate }}</div>
            </div>
            <div class="w-50">
                <input type="text" class="form-control" [(ngModel)]="filePrefix" (change)="saveConfig()" placeholder="asciinema">
            </div>
        </div>

        <div class="form-line mb-3">
            <div class="header">
                <div class="title">{{ 'Idle Time Limit (Seconds)' | translate }}</div>
                <div class="description">{{ 'Limit maximum idle time during playback (0 for no limit / keep 100% original timing)' | translate }}</div>
            </div>
            <div class="w-50">
                <input type="number" step="0.5" min="0" class="form-control" [(ngModel)]="idleTimeLimit" (change)="saveConfig()" placeholder="2.0">
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

        <!-- Interactive Sensitive Data Scanner & Masking Section -->
        <h3 class="mt-4 mb-3">{{ 'Interactive Sensitive Data Scanner & Masking Tool' | translate }}</h3>

        <div class="card p-3 mb-4 guide-card">
            <p class="guide-text small mb-3">
                {{ 'Scan recorded .cast files to detect & mask IPs, API tokens, passwords interactively' | translate }}
            </p>

            <div class="d-flex gap-2 mb-3">
                <button class="btn btn-primary btn-sm" (click)="scanRecentFile()">
                    {{ 'Scan & Mask Recent File' | translate }}
                </button>
                <button class="btn btn-outline-info btn-sm" (click)="triggerFileSelectForScan()">
                    {{ 'Select & Scan .cast File' | translate }}
                </button>
                <input #scanFileInput type="file" accept=".cast" style="display: none" (change)="onScanFileSelected($event)">
            </div>

            <div *ngIf="scannedFilePath" class="mb-3">
                <div class="small fw-bold text-info mb-2">Target File: {{ scannedFilePath }}</div>

                <div *ngIf="detectedItems.length === 0" class="alert alert-secondary py-2 small mb-3">
                    {{ 'No sensitive data detected in file.' | translate }}
                </div>

                <div *ngIf="detectedItems.length > 0" class="mb-3">
                    <h6 class="small fw-bold mb-2">{{ 'Detected Sensitive Items' | translate }}:</h6>
                    <div class="list-group mb-3">
                        <label *ngFor="let item of detectedItems" class="list-group-item list-group-item-dark d-flex align-items-center justify-content-between py-2 px-3 small">
                            <div>
                                <input class="form-check-input me-2" type="checkbox" [(ngModel)]="item.enabled">
                                <span class="badge bg-secondary me-2">{{ item.type }}</span>
                                <code class="text-warning">{{ item.value }}</code>
                            </div>
                            <span class="badge bg-primary rounded-pill">{{ item.count }} hits</span>
                        </label>
                    </div>
                </div>

                <div class="input-group w-75 mb-3">
                    <input type="text" class="form-control form-control-sm" [(ngModel)]="customWord" [placeholder]="'Add Custom Word' | translate">
                    <button class="btn btn-outline-secondary btn-sm" (click)="addCustomWord()">{{ 'Add Word' | translate }}</button>
                </div>

                <button class="btn btn-success btn-sm" (click)="applyMasking()">
                    {{ 'Apply Masking & Save As New File' | translate }}
                </button>
            </div>
        </div>

        <!-- Upload to asciinema.org Section -->
        <h3 class="mt-4 mb-3">{{ 'Upload Recording to asciinema.org' | translate }}</h3>

        <div class="card p-3 mb-4 guide-card">
            <p class="guide-text small mb-3">
                {{ 'Upload recent .cast file to asciinema.org with custom title for easy web sharing' | translate }}
            </p>

            <div class="mb-3 w-75">
                <label class="form-label small fw-bold">Target File Path (.cast)</label>
                <div class="input-group">
                    <input type="text" class="form-control form-control-sm font-monospace" [(ngModel)]="uploadFilePath" placeholder="/path/to/recording.cast">
                    <button class="btn btn-outline-secondary btn-sm" (click)="triggerFileSelectForUpload()">Select File</button>
                    <input #uploadFileInput type="file" accept=".cast" style="display: none" (change)="onUploadFileSelected($event)">
                </div>
            </div>

            <div class="input-group w-75 mb-3">
                <span class="input-group-text fw-bold small">Title</span>
                <input type="text" class="form-control" [(ngModel)]="uploadTitle" placeholder="My Terminal Session Title">
                <button class="btn btn-primary" [disabled]="isUploading || !uploadFilePath" (click)="uploadSpecifiedFile()">
                    {{ isUploading ? ('Uploading to asciinema.org...' | translate) : ('Upload File to asciinema.org' | translate) }}
                </button>
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
                <input type="text" class="form-control font-monospace" [value]="'asciinema play &quot;' + savePath + '/filename.cast&quot;'" readonly>
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
    @ViewChild('scanFileInput') scanFileInput?: ElementRef<HTMLInputElement>
    @ViewChild('uploadFileInput') uploadFileInput?: ElementRef<HTMLInputElement>

    cliInfo?: CLIInfo
    scannedFilePath: string | null = null
    detectedItems: DetectedItem[] = []
    customWord: string = ''
    uploadFilePath: string = ''
    uploadTitle: string = ''
    isUploading: boolean = false

    constructor(
        private config: ConfigService,
        private platform: PlatformService,
        private notifications: NotificationsService,
        private translate: TranslateService,
        private recorder: AsciinemaRecorderService,
    ) {
        registerPluginTranslations(this.translate)
    }

    get formatVersion(): string {
        return this.config.store.pluginConfig?.['asciinema']?.formatVersion || 'v2'
    }

    set formatVersion(val: string) {
        this.updatePluginConfig('formatVersion', val)
    }

    get filenamePattern(): string {
        return this.config.store.pluginConfig?.['asciinema']?.filenamePattern || '{host}_{date}'
    }

    set filenamePattern(val: string) {
        this.updatePluginConfig('filenamePattern', val)
    }

    get filePrefix(): string {
        return this.config.store.pluginConfig?.['asciinema']?.filePrefix || 'asciinema'
    }

    set filePrefix(val: string) {
        this.updatePluginConfig('filePrefix', val)
    }

    get idleTimeLimit(): number {
        const val = Number(this.config.store.pluginConfig?.['asciinema']?.idleTimeLimit)
        return isNaN(val) ? 2.0 : val
    }

    set idleTimeLimit(val: number) {
        this.updatePluginConfig('idleTimeLimit', val)
    }

    get savePath(): string {
        return this.config.store.pluginConfig?.['asciinema']?.savePath || path.join(os.homedir(), 'Downloads', 'AsciinemaRecordings')
    }

    set savePath(val: string) {
        this.updatePluginConfig('savePath', val)
    }

    private updatePluginConfig(key: string, val: any): void {
        const current = this.config.store.pluginConfig || {}
        this.config.store.pluginConfig = {
            ...current,
            asciinema: {
                ...(current['asciinema'] || {}),
                [key]: val,
            },
        }
    }

    async ngOnInit() {
        await this.checkCLI()
        if (this.recorder.lastRecordedFilePath) {
            this.uploadFilePath = this.recorder.lastRecordedFilePath
        }
    }

    saveConfig() {
        this.config.save()
    }

    async checkCLI() {
        this.cliInfo = await detectAsciinemaCLI()
    }

    triggerFileSelectForScan() {
        this.scanFileInput?.nativeElement.click()
    }

    onScanFileSelected(event: Event) {
        const input = event.target as HTMLInputElement
        if (input.files && input.files.length > 0) {
            const file = input.files[0]
            this.performScan((file as any).path || file.name)
        }
    }

    triggerFileSelectForUpload() {
        this.uploadFileInput?.nativeElement.click()
    }

    onUploadFileSelected(event: Event) {
        const input = event.target as HTMLInputElement
        if (input.files && input.files.length > 0) {
            const file = input.files[0]
            this.uploadFilePath = (file as any).path || file.name
        }
    }

    async uploadSpecifiedFile() {
        const targetPath = this.uploadFilePath
        if (!targetPath || !fs.existsSync(targetPath)) {
            this.notifications.error(this.translate.instant('Upload Failed'), 'File not found: ' + targetPath)
            return
        }

        this.isUploading = true
        try {
            if (this.uploadTitle && this.uploadTitle.trim()) {
                const lines = fs.readFileSync(targetPath, 'utf8').split('\n')
                if (lines.length > 0 && lines[0].trim()) {
                    try {
                        const header = JSON.parse(lines[0])
                        header.title = this.uploadTitle.trim()
                        lines[0] = JSON.stringify(header)
                        fs.writeFileSync(targetPath, lines.join('\n'), 'utf8')
                    } catch (e) {}
                }
            }

            const url = await this.recorder.uploadToAsciinema(targetPath)
            this.platform.setClipboard({ text: url })
            this.notifications.info(
                this.translate.instant('Uploaded to asciinema.org successfully!'),
                `${this.translate.instant('Web URL copied to clipboard:')}\n${url}`,
            )
        } catch (e: any) {
            this.notifications.error(this.translate.instant('Upload Failed'), e.message || String(e))
        } finally {
            this.isUploading = false
        }
    }

    scanRecentFile() {
        const folder = this.savePath
        if (!fs.existsSync(folder)) {
            this.notifications.notice(this.translate.instant('No recent .cast recording file found.'))
            return
        }

        const files = fs.readdirSync(folder).filter(f => f.endsWith('.cast')).map(f => path.join(folder, f))
        if (files.length === 0) {
            this.notifications.notice(this.translate.instant('No recent .cast recording file found.'))
            return
        }

        files.sort((a, b) => fs.statSync(b).mtimeMs - fs.statSync(a).mtimeMs)
        this.performScan(files[0])
    }

    performScan(filePath: string) {
        try {
            const content = fs.readFileSync(filePath, 'utf8')
            this.scannedFilePath = filePath
            this.detectedItems = scanSensitiveData(content)
        } catch (e: any) {
            this.notifications.error(this.translate.instant('Recording Error'), e.message)
        }
    }

    addCustomWord() {
        if (!this.customWord || !this.customWord.trim()) {
            return
        }
        const val = this.customWord.trim()
        if (!this.detectedItems.some(i => i.value === val)) {
            this.detectedItems.unshift({
                value: val,
                type: 'Custom Word',
                count: 1,
                enabled: true,
            })
        }
        this.customWord = ''
    }

    applyMasking() {
        if (!this.scannedFilePath || !fs.existsSync(this.scannedFilePath)) {
            return
        }

        const selectedKeywords = this.detectedItems.filter(i => i.enabled).map(i => i.value)
        if (selectedKeywords.length === 0) {
            this.notifications.notice('No keywords selected for masking.')
            return
        }

        try {
            const content = fs.readFileSync(this.scannedFilePath, 'utf8')
            const maskedContent = maskCastContent(content, selectedKeywords, '***')

            const dir = path.dirname(this.scannedFilePath)
            const ext = path.extname(this.scannedFilePath)
            const name = path.basename(this.scannedFilePath, ext)

            const newFilePath = path.join(dir, `${name}_masked${ext}`)
            fs.writeFileSync(newFilePath, maskedContent, 'utf8')

            this.uploadFilePath = newFilePath
            this.platform.setClipboard({ text: newFilePath })
            this.notifications.info(
                this.translate.instant('Masked file saved successfully'),
                newFilePath,
            )
        } catch (e: any) {
            this.notifications.error(this.translate.instant('Save Failed'), e.message)
        }
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
