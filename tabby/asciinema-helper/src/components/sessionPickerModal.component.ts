import { Component, OnInit, OnDestroy, Input } from '@angular/core'
import { NgbActiveModal } from '@ng-bootstrap/ng-bootstrap'
import { PlatformService, NotificationsService, TranslateService } from 'tabby-core'
import { BaseTerminalTabComponent } from 'tabby-terminal'
import { AsciinemaRecorderService } from '../services/recorder.service'
import { registerPluginTranslations } from '../i18n'
import { Subscription } from 'rxjs'
import * as path from 'path'

export interface DiscoveredSession {
    name: string
    detail: string
    type: 'docker' | 'tmux' | 'herdr'
}

@Component({
    selector: 'asciinema-session-picker-modal',
    template: `
        <div class="modal-header">
            <h5 class="modal-title">{{ 'Session Discovery & Custom Record' | translate }}</h5>
            <button type="button" class="btn-close btn-close-white" (click)="close()"></button>
        </div>

        <div class="modal-body">
            <!-- Target Session Selection -->
            <div class="mb-3">
                <label class="form-label small fw-bold">{{ 'Target Session Type' | translate }}</label>
                <div class="btn-group w-100 mb-2">
                    <button type="button" class="btn btn-sm" [class.btn-primary]="targetType === 'docker'" [class.btn-outline-secondary]="targetType !== 'docker'" (click)="setTargetType('docker')">
                        {{ 'Docker Container Logs' | translate }}
                    </button>
                    <button type="button" class="btn btn-sm" [class.btn-primary]="targetType === 'tmux'" [class.btn-outline-secondary]="targetType !== 'tmux'" (click)="setTargetType('tmux')">
                        {{ 'Tmux Session' | translate }}
                    </button>
                    <button type="button" class="btn btn-sm" [class.btn-primary]="targetType === 'herdr'" [class.btn-outline-secondary]="targetType !== 'herdr'" (click)="setTargetType('herdr')">
                        {{ 'Herdr Session' | translate }}
                    </button>
                    <button type="button" class="btn btn-sm" [class.btn-primary]="targetType === 'none'" [class.btn-outline-secondary]="targetType !== 'none'" (click)="setTargetType('none')">
                        {{ 'Terminal' | translate }}
                    </button>
                </div>
            </div>

            <!-- Discovered Session List -->
            <div *ngIf="targetType !== 'none'" class="mb-3">
                <div class="d-flex align-items-center justify-content-between mb-1">
                    <label class="form-label small fw-bold mb-0">
                        {{ targetType === 'docker' ? ('Docker Container List' | translate) : (targetType === 'tmux' ? ('Tmux Session List' | translate) : ('Herdr Session List' | translate)) }}
                    </label>
                    <button type="button" class="btn btn-link btn-sm p-0 text-decoration-none" (click)="refreshSessionList()">
                        [{{ 'Refresh List' | translate }}]
                    </button>
                </div>

                <div class="list-group mb-2 style-session-list" style="max-height: 160px; overflow-y: auto;">
                    <button *ngFor="let item of sessionList" type="button" class="list-group-item list-group-item-action py-1 px-2 small d-flex justify-content-between align-items-center" [class.active]="sessionName === item.name" (click)="selectSession(item.name)">
                        <span class="fw-bold font-monospace text-truncate" style="max-width: 240px;">{{ item.name }}</span>
                        <span class="badge bg-secondary opacity-75" style="font-size: 10px;">{{ item.detail }}</span>
                    </button>

                    <div *ngIf="sessionList.length === 0 && !isScanning" class="p-2 text-center text-muted small border rounded bg-dark">
                        {{ 'No active sessions found. Enter name manually below or click Refresh.' | translate }}
                    </div>

                    <div *ngIf="isScanning" class="p-2 text-center text-info small border rounded bg-dark">
                        {{ 'Scanning active sessions...' | translate }}
                    </div>
                </div>

                <input type="text" class="form-control form-control-sm font-monospace" [(ngModel)]="sessionName" (ngModelChange)="onSessionNameInput($event)" [placeholder]="targetType === 'docker' ? ('e.g. my-app-container' | translate) : (targetType === 'tmux' ? ('e.g. prod-logs' | translate) : ('e.g. main or p1' | translate))">
            </div>

            <!-- One-off Custom Settings -->
            <h6 class="border-top pt-3 mb-2 small fw-bold text-info">
                {{ 'One-off Custom Settings (Applies to this recording only)' | translate }}
            </h6>

            <div class="row g-2 mb-3">
                <div class="col-6">
                    <label class="form-label small text-muted mb-1">{{ 'Recording Timer (Minutes)' | translate }}</label>
                    <input type="number" min="0" max="1440" class="form-control form-control-sm" [(ngModel)]="timerMinutes" placeholder="0">
                </div>
                <div class="col-6">
                    <label class="form-label small text-muted mb-1">{{ 'Single File Limit (MB)' | translate }}</label>
                    <input type="number" min="1" max="30" class="form-control form-control-sm" [(ngModel)]="customFileLimitMB" placeholder="8">
                </div>
            </div>

            <div class="mb-3">
                <label class="form-label small text-muted mb-1">{{ 'Max Split File Count' | translate }}</label>
                <input type="number" min="0" max="50" class="form-control form-control-sm" [(ngModel)]="customMaxSplits" placeholder="0">
            </div>

            <!-- Command Preview -->
            <div class="mb-2">
                <label class="form-label small fw-bold text-muted">{{ 'Generated Command Preview' | translate }}</label>
                <div class="bg-dark p-2 rounded border border-secondary font-monospace small text-warning text-break">
                    {{ buildGeneratedCommand() }}
                </div>
            </div>
        </div>

        <div class="modal-footer">
            <button type="button" class="btn btn-outline-secondary btn-sm me-auto" (click)="copyGeneratedCommand()">
                {{ 'Copy Command' | translate }}
            </button>
            <button type="button" class="btn btn-secondary btn-sm" (click)="close()">
                {{ 'Cancel' | translate }}
            </button>
            <button type="button" class="btn btn-primary btn-sm" (click)="startCustomRecord()">
                {{ 'Start Recording' | translate }}
            </button>
        </div>
    `,
    styles: [`
        :host { display: block; }
        .style-session-list .list-group-item.active { background-color: #0d6efd; border-color: #0d6efd; }
    `]
})
export class AsciinemaSessionPickerModalComponent implements OnInit, OnDestroy {
    @Input() activeTab: BaseTerminalTabComponent<any> | null = null

    targetType: 'docker' | 'tmux' | 'herdr' | 'none' = 'none'
    sessionName: string = ''
    timerMinutes: number = 0
    customFileLimitMB: number = 8
    customMaxSplits: number = 0

    sessionList: DiscoveredSession[] = []
    isScanning: boolean = false
    private activeSubscription: Subscription | null = null
    private activeTimer: any = null

    constructor(
        public modal: NgbActiveModal,
        private platform: PlatformService,
        private notifications: NotificationsService,
        private translate: TranslateService,
        private recorder: AsciinemaRecorderService,
    ) {
        registerPluginTranslations(this.translate)
    }

    ngOnInit() {
        if (this.targetType !== 'none') {
            this.refreshSessionList()
        }
    }

    ngOnDestroy() {
        this.cleanupScan()
    }

    setTargetType(type: 'docker' | 'tmux' | 'herdr' | 'none') {
        this.targetType = type
        this.sessionName = ''
        this.sessionList = []
        if (type !== 'none') {
            this.refreshSessionList()
        }
    }

    selectSession(name: string) {
        this.sessionName = this.sanitizeSessionName(name)
    }

    onSessionNameInput(val: string) {
        this.sessionName = this.sanitizeSessionName(val)
    }

    private sanitizeSessionName(name: string): string {
        if (!name) return ''
        return name.trim().replace(/[/\\;|$&`"'\s\t\r\n]+/g, '')
    }

    close() {
        this.cleanupScan()
        this.modal.dismiss()
    }

    private cleanupScan() {
        if (this.activeSubscription) {
            this.activeSubscription.unsubscribe()
            this.activeSubscription = null
        }
        if (this.activeTimer) {
            clearTimeout(this.activeTimer)
            this.activeTimer = null
        }
        this.isScanning = false
    }

    private stripAnsi(str: string): string {
        return str
            .replace(/\u001b\][^\u0007\u001b]*(?:\u0007|\u001b\\)/g, '')
            .replace(/[\u001b\u009b][[()#;?]*(?:[0-9]{1,4}(?:;[0-9]{0,4})*)?[0-9A-ORZcf-nary=<>]|[\r]/g, '')
            .replace(/\r\n/g, '\n')
    }

    refreshSessionList() {
        if (this.targetType === 'none') {
            return
        }

        this.cleanupScan()
        this.isScanning = true
        this.sessionList = []

        const session = (this.activeTab as any)?.session
        if (!session) {
            this.isScanning = false
            return
        }

        let scanCmd = ''
        if (this.targetType === 'docker') {
            scanCmd = 'docker ps --format "{{.Names}}|||{{.Image}} ({{.Status}})"'
        } else if (this.targetType === 'tmux') {
            scanCmd = 'tmux ls'
        } else if (this.targetType === 'herdr') {
            scanCmd = 'herdr ls'
        }

        let capturedOutput = ''
        this.activeSubscription = session.output$.subscribe((data: string) => {
            capturedOutput += data
        })

        // Simple leading space command execution to prevent history logging
        session.write(` ${scanCmd}\r`)

        this.activeTimer = setTimeout(() => {
            if (this.activeSubscription) {
                this.activeSubscription.unsubscribe()
                this.activeSubscription = null
            }
            try { session.write('\r\x1b[2K') } catch (e) {}
            this.isScanning = false
            this.parseTerminalOutput(this.stripAnsi(capturedOutput))
        }, 200)
    }

    private parseTerminalOutput(output: string) {
        const lower = output.toLowerCase()
        if (
            lower.includes('command not found') ||
            lower.includes('not found') ||
            lower.includes('unknown command') ||
            lower.includes('no such file') ||
            lower.includes('daemon not running')
        ) {
            this.sessionList = []
            return
        }

        const lines = output.split('\n').map(l => l.trim()).filter(l => l.length > 0)
        const discovered: DiscoveredSession[] = []

        if (this.targetType === 'docker') {
            for (const line of lines) {
                if (line.includes('|||')) {
                    const parts = line.split('|||')
                    const name = this.sanitizeSessionName(parts[0])
                    const detail = parts[1] ? parts[1].trim() : 'Docker Container'
                    if (name && !name.includes('docker ps')) {
                        discovered.push({ name, detail, type: 'docker' })
                    }
                }
            }
        } else if (this.targetType === 'tmux') {
            for (const line of lines) {
                if (line.includes(':') && (line.includes('windows') || line.includes('attached') || line.includes('created'))) {
                    const idx = line.indexOf(':')
                    const name = this.sanitizeSessionName(line.substring(0, idx))
                    const detail = line.substring(idx + 1).trim()
                    if (name && !name.includes('tmux ls')) {
                        discovered.push({ name, detail, type: 'tmux' })
                    }
                }
            }
        } else if (this.targetType === 'herdr') {
            const cleanLines = lines.filter(l => {
                const clean = l.replace(/^[\$>\s#]+/, '').trim()
                return clean.length > 0 && !clean.includes('herdr ls') && !clean.includes(']8;;')
            })

            let headerSkipped = false
            for (const line of cleanLines) {
                const cleanLine = line.replace(/^[└├─│\s\t\d+.\-:]+/, '').trim()
                if (!cleanLine) continue

                const upper = cleanLine.toUpperCase()
                if (!headerSkipped && (upper.startsWith('PANE') || upper.startsWith('NAME') || upper.startsWith('ID') || upper.startsWith('SESSION'))) {
                    headerSkipped = true
                    continue
                }

                const parts = cleanLine.split(/\s+/)
                const name = parts[0] ? this.sanitizeSessionName(parts[0]) : ''

                if (name && !['herdr', 'ls', 'unknown', 'run', 'command', 'zsh', 'bash'].includes(name.toLowerCase())) {
                    const rest = parts.slice(1).join(' ')
                    const isPane = line.includes('pane') || name.startsWith('p') || name.startsWith('pane')
                    const typeLabel = isPane ? 'Herdr Pane' : 'Herdr Space'
                    const detail = rest ? `${typeLabel} (${rest})` : typeLabel

                    if (!discovered.some(d => d.name === name)) {
                        discovered.push({ name, detail, type: 'herdr' })
                    }
                }
            }
        }

        this.sessionList = discovered
    }

    getPrefixName(): string {
        const cleanName = this.sanitizeSessionName(this.sessionName)
        if (this.targetType === 'docker' && cleanName) return `docker_${cleanName}`
        if (this.targetType === 'tmux' && cleanName) return `tmux_${cleanName}`
        if (this.targetType === 'herdr' && cleanName) return `herdr_${cleanName}`
        return ''
    }

    buildGeneratedCommand(): string {
        let innerCmd = ''
        const cleanName = this.sanitizeSessionName(this.sessionName)
        const prefix = this.getPrefixName() || 'session'

        if (this.targetType === 'docker' && cleanName) innerCmd = `docker logs -f --tail=200 ${cleanName}`
        else if (this.targetType === 'tmux' && cleanName) innerCmd = `tmux attach -t ${cleanName}`
        else if (this.targetType === 'herdr' && cleanName) innerCmd = `herdr attach -t ${cleanName}`

        const dateStr = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19)
        const castPath = path.join(this.recorder.savePath, `${dateStr}_${prefix}.cast`)

        return innerCmd ? `asciinema rec -c "${innerCmd}" "${castPath}"` : `asciinema rec "${castPath}"`
    }

    copyGeneratedCommand() {
        this.platform.setClipboard({ text: this.buildGeneratedCommand() })
        this.notifications.notice(this.translate.instant('Copied to clipboard.'))
    }

    startCustomRecord() {
        this.modal.close({
            command: this.buildGeneratedCommand(),
            sessionPrefix: this.getPrefixName(),
            timerMinutes: this.timerMinutes,
            customFileLimitMB: this.customFileLimitMB,
            customMaxSplits: this.customMaxSplits,
        })
    }
}
