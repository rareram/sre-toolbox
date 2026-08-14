import { Component, OnInit, ElementRef, ViewChild } from '@angular/core'
import { ConfigService, NotificationsService, PlatformService, TranslateService } from 'tabby-core'
import { detectAsciinemaCLI, CLIInfo } from '../services/cliDetector'
import { scanSensitiveData, maskCastContent, DetectedItem } from '../services/maskingScanner'
import { AsciinemaRecorderService } from '../services/recorder.service'
import { registerPluginTranslations } from '../i18n'
import { STANDALONE_PLAYER_HTML } from '../utils/standalonePlayerHtml'
import * as os from 'os'
import * as path from 'path'
import * as fs from 'fs'

@Component({
    selector: 'asciinema-settings-tab',
    template: `
        <h3 class="mb-3">{{ 'Asciinema Recording Settings' | translate }}</h3>

        <!-- CLI Not Required Assurance Notice Banner (2-line clean format, optional phrasing) -->
        <div class="alert alert-info py-2 px-3 mb-4 small d-flex align-items-center">
            <span class="me-2 fs-5">💡</span>
            <div>
                <div>{{ 'Notice: Asciinema CLI is optional for recording in Tabby.' | translate }}</div>
                <div class="opacity-75">{{ '(CLI is only needed to play recordings in terminal: $ asciinema play)' | translate }}</div>
            </div>
        </div>

        <!-- Section 0: Toolbar Buttons Display Settings (Top Placement) -->
        <div class="form-line border-bottom-0 pb-1">
            <div class="header">
                <div class="title">{{ 'Toolbar Buttons Display' | translate }}</div>
                <div class="description">
                    {{ 'Configure visibility of Asciinema buttons on the top toolbar' | translate }}
                    <span class="text-info ms-1">({{ 'Requires Tabby restart' | translate }})</span>
                </div>
            </div>
        </div>

        <div class="form-line ps-4 pt-1 border-top-0 border-bottom-0 pb-1 sub-option-line">
            <div class="header border-start border-2 border-info ps-2">
                <div class="title small text-muted">{{ 'Show Quick Record Button' | translate }}</div>
                <div class="description small">{{ 'Show single triangle (▶) toggle button on the toolbar (Ctrl+Shift+R)' | translate }}</div>
            </div>
            <div class="form-check form-switch m-0 p-0">
                <input class="form-check-input ms-0 me-2" type="checkbox" role="switch" style="width: 2.5em; height: 1.25em;" [(ngModel)]="showQuickRecordButton" (change)="saveConfig()">
            </div>
        </div>

        <div class="form-line ps-4 pt-1 border-top-0 mb-3 sub-option-line">
            <div class="header border-start border-2 border-info ps-2">
                <div class="title small text-muted">{{ 'Show Session Discovery Button' | translate }}</div>
                <div class="description small">{{ 'Show twin triangle (▶▶) headless target session discovery modal button' | translate }}</div>
            </div>
            <div class="form-check form-switch m-0 p-0">
                <input class="form-check-input ms-0 me-2" type="checkbox" role="switch" style="width: 2.5em; height: 1.25em;" [(ngModel)]="showSessionPickerButton" (change)="saveConfig()">
            </div>
        </div>

        <!-- Section 1: Basic Recording & Storage Limits -->
        <div class="form-line">
            <div class="header">
                <div class="title">{{ 'Format Version' | translate }}</div>
                <div class="description">{{ 'Choose asciinema format version (v2 recommended for broad compatibility)' | translate }}</div>
            </div>
            <select class="form-control w-50" [(ngModel)]="formatVersion" (change)="saveConfig()">
                <option value="v2">{{ 'v2 (Standard, Recommended)' | translate }}</option>
                <option value="v3">{{ 'v3 (Experimental, May have playback issues)' | translate }}</option>
            </select>
        </div>

        <!-- Parent Option: Filename Pattern -->
        <div class="form-line border-bottom-0 pb-1">
            <div class="header">
                <div class="title">{{ 'Filename Pattern' | translate }}</div>
                <div class="description">
                    {{ 'Template pattern for .cast filenames' | translate }}
                    <span class="text-info ms-2">
                        ({{ 'Variables' | translate }}: <code>[host]</code>, <code>[date]</code>, <code>[prefix]</code> | <code>[]</code>, <code>&#123;&#125;</code>, <code>%%</code> {{ 'supported' | translate }})
                    </span>
                </div>
            </div>
            <input type="text" class="form-control w-50" [(ngModel)]="filenamePattern" (change)="saveConfig()" [attr.placeholder]="'{date}_{host}'">
        </div>

        <!-- Child Option: Default Prefix -->
        <div class="form-line ps-4 pt-1 border-top-0 sub-option-line">
            <div class="header border-start border-2 border-info ps-2">
                <div class="title small text-muted">{{ 'Default Prefix' | translate }}</div>
                <div class="description small">{{ 'Fallback string used for [prefix] variable in filename pattern' | translate }}</div>
            </div>
            <input type="text" class="form-control w-50 form-control-sm" [(ngModel)]="filePrefix" (change)="saveConfig()" placeholder="asciinema">
        </div>

        <div class="form-line">
            <div class="header">
                <div class="title">{{ 'Idle Time Limit (Seconds)' | translate }}</div>
                <div class="description">{{ 'Cap idle pauses during playback (Default: 2.0s | 0 for no limit)' | translate }}</div>
            </div>
            <input type="number" step="0.5" min="0" class="form-control w-50" [(ngModel)]="idleTimeLimit" (change)="saveConfig()" placeholder="2.0">
        </div>

        <!-- Parent Option: Single File Size Limit -->
        <div class="form-line border-bottom-0 pb-1">
            <div class="header">
                <div class="title">{{ 'Single File Size Limit (MB)' | translate }}</div>
                <div class="description">{{ 'Maximum size per recording file (Default: 8 MB | Max: 30 MB)' | translate }}</div>
            </div>
            <input type="number" min="1" max="30" class="form-control w-50" [(ngModel)]="maxSingleFileSizeMB" (change)="saveConfig()" placeholder="8">
        </div>

        <div *ngIf="maxSingleFileSizeMB > 8" class="alert alert-warning py-1 px-3 my-2 small fw-bold">
            {{ 'Files over 8 MB may fail to upload to asciinema.org (Local playback only)' | translate }}
        </div>

        <!-- Child Option 1: Auto-Split Files on Size Limit -->
        <div class="form-line ps-4 pt-1 border-top-0 border-bottom-0 pb-1 sub-option-line">
            <div class="header border-start border-2 border-info ps-2">
                <div class="title small text-muted">{{ 'Auto-Split Files on Size Limit' | translate }}</div>
                <div class="description small">{{ 'Automatically split into multiple .cast files (_2, _3) when size limit is reached' | translate }}</div>
            </div>
            <div class="form-check form-switch m-0 p-0">
                <input class="form-check-input ms-0 me-2" type="checkbox" role="switch" style="width: 2.5em; height: 1.25em;" [(ngModel)]="enableFileSplitting" (change)="saveConfig()">
            </div>
        </div>

        <!-- Child Option 2: Max Split File Count (Only visible when Auto-Split is enabled) -->
        <div *ngIf="enableFileSplitting" class="form-line ps-4 pt-1 border-top-0 sub-option-line">
            <div class="header border-start border-2 border-info ps-2">
                <div class="title small text-muted">{{ 'Max Split File Count' | translate }}</div>
                <div class="description small">
                    {{ 'Maximum number of split parts (0: Auto-calculated based on total storage limit)' | translate }}
                    <span class="text-info fw-bold ms-1">(Max ~{{ calculatedMaxParts }} parts for {{ maxStorageMB }}MB)</span>
                </div>
            </div>
            <input type="number" min="0" max="50" class="form-control w-50 form-control-sm" [(ngModel)]="maxSplitCount" (change)="saveConfig()" placeholder="0">
        </div>

        <div class="form-line">
            <div class="header">
                <div class="title">{{ 'Total Storage Limit (MB)' | translate }}</div>
                <div class="description">{{ 'Total storage capacity for recordings (Default: 100 MB | Auto-cleans old files when full)' | translate }}</div>
            </div>
            <input type="number" min="10" class="form-control w-50" [(ngModel)]="maxStorageMB" (change)="saveConfig()" placeholder="100">
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

        <!-- Section 2: Interactive Sensitive Data Scanner & Masking Section -->
        <h3 class="mt-4 mb-3">{{ 'Interactive Sensitive Data Scanner & Masking Tool' | translate }}</h3>

        <div class="card p-3 mb-4 guide-card">
            <p class="guide-text small mb-3">
                {{ 'Scan .cast files to detect and redact sensitive IPs, tokens, and passwords' | translate }}
            </p>

            <!-- Parent Option: Masking Replacement Preset Buttons -->
            <div class="form-line border-0 pt-0 pb-2 mb-1">
                <div class="header">
                    <div class="title">{{ 'Masking Replacement Character' | translate }}</div>
                    <div class="description">{{ 'Masking replacement character (Preserves 1:1 terminal display width)' | translate }}</div>
                </div>
                <div class="btn-group w-50">
                    <button type="button" class="btn btn-sm" [class.btn-primary]="maskingChar === '*'" [class.btn-outline-secondary]="maskingChar !== '*'" (click)="setMaskingChar('*')">* (Asterisk)</button>
                    <button type="button" class="btn btn-sm" [class.btn-primary]="maskingChar === '█'" [class.btn-outline-secondary]="maskingChar !== '█'" (click)="setMaskingChar('█')">█ (Full Block)</button>
                    <button type="button" class="btn btn-sm" [class.btn-primary]="maskingChar === '▒'" [class.btn-outline-secondary]="maskingChar !== '▒'" (click)="setMaskingChar('▒')">▒ (Shade)</button>
                </div>
            </div>

            <!-- Child Option: Custom Masking Input -->
            <div class="form-line border-0 pt-1 pb-3 mb-3 ps-4 sub-option-line">
                <div class="header border-start border-2 border-info ps-2">
                    <div class="title small text-muted">{{ 'Custom Masking Char (e.g. *, #, █)' | translate }}</div>
                </div>
                <input type="text" class="form-control form-control-sm w-50 text-center" [ngModel]="maskingChar" (ngModelChange)="setMaskingChar($event)" [placeholder]="'Custom Masking Char (e.g. *, #, █)' | translate">
            </div>

            <div class="d-flex gap-2 mb-3">
                <button class="btn btn-primary" (click)="scanRecentFile()">
                    {{ 'Scan & Mask Recent File' | translate }}
                </button>
                <button class="btn btn-outline-info" (click)="triggerFileSelectForScan()">
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
                        <label *ngFor="let item of detectedItems" class="list-group-item bg-transparent border border-secondary text-light d-flex align-items-center justify-content-between py-2 px-3 small mb-1 rounded">
                            <div>
                                <input class="form-check-input me-2" type="checkbox" [(ngModel)]="item.enabled">
                                <span class="badge bg-info text-dark me-2">{{ item.type }}</span>
                                <code class="text-warning font-monospace">{{ item.value }}</code>
                            </div>
                            <span class="badge bg-secondary rounded-pill">{{ item.count }} hits</span>
                        </label>
                    </div>
                </div>

                <div class="input-group w-75 mb-3">
                    <input type="text" class="form-control" [(ngModel)]="customWord" [placeholder]="'Add Custom Word' | translate">
                    <button class="btn btn-outline-secondary" (click)="addCustomWord()">{{ 'Add Word' | translate }}</button>
                </div>

                <button class="btn btn-success" (click)="applyMasking()">
                    {{ 'Apply Masking & Save As New File' | translate }}
                </button>
            </div>
        </div>

        <!-- Section 3: Upload to asciinema.org Section -->
        <h3 class="mt-4 mb-3">{{ 'Web Upload & Link Sharing (asciinema.org)' | translate }}</h3>

        <div class="card p-3 mb-4 guide-card">
            <p class="guide-text small mb-2">
                {{ 'Upload .cast files to asciinema.org for instant web link sharing' | translate }}
            </p>
            <div class="alert alert-secondary py-2 px-3 mb-3 small">
                <div>{{ 'Optional: Web upload is completely optional.' | translate }}</div>
                <div>{{ 'No account required to upload (claim anytime via asciinema auth).' | translate }}</div>
            </div>

            <div class="form-line border-0 pt-0 pb-2">
                <div class="header">
                    <div class="title">{{ 'Target File Select (.cast)' | translate }}</div>
                </div>
                <div class="input-group w-50">
                    <input type="text" class="form-control font-monospace" [(ngModel)]="uploadFilePath" placeholder="/path/to/recording.cast">
                    <button class="btn btn-outline-secondary" (click)="triggerFileSelectForUpload()">{{ 'Browse' | translate }}</button>
                    <input #uploadFileInput type="file" accept=".cast" style="display: none" (change)="onUploadFileSelected($event)">
                </div>
            </div>

            <div class="form-line border-0 pt-0 pb-3">
                <div class="header">
                    <div class="title">{{ 'Upload File Title (asciinema.org)' | translate }}</div>
                </div>
                <div class="input-group w-50">
                    <input type="text" class="form-control" [(ngModel)]="uploadTitle" placeholder="My Terminal Session Title">
                    <button class="btn btn-primary" [disabled]="isUploading || !uploadFilePath" (click)="uploadSpecifiedFile()">
                        {{ isUploading ? ('Uploading...' | translate) : ('Upload' | translate) }}
                    </button>
                </div>
            </div>
        </div>

        <!-- Section 4: 3-Step Playback Guide -->
        <h3 class="mt-4 mb-3">{{ '3 Ways to Play .cast Session Recordings' | translate }}</h3>

        <div class="card p-3 mb-4 guide-card">
            <!-- Method 1: Hotkey Quick Playback -->
            <div class="mb-3">
                <h5 class="mb-2 guide-title text-info fw-bold">{{ 'Method 1 (Fastest): Hotkey Quick Playback (Ctrl+Shift+P)' | translate }}</h5>
                <p class="guide-text small mb-0">
                    {{ 'Press Ctrl+Shift+P in terminal to instantly play the latest recording:' | translate }}
                    <span class="badge bg-primary ms-1 font-monospace">Ctrl + Shift + P</span>
                </p>
            </div>

            <!-- Method 2: Standalone HTML Player -->
            <div class="border-top pt-3 mb-3">
                <h5 class="mb-2 guide-title text-info fw-bold">{{ 'Method 2 (No CLI Needed): Standalone HTML Web Player' | translate }}</h5>
                <p class="guide-text small mb-2">
                    {{ 'Download standalone HTML web player to view .cast recordings in browser without CLI or server:' | translate }}
                </p>
                <div>
                    <button class="btn btn-outline-primary" (click)="downloadStandalonePlayer()">
                        {{ 'Download Standalone HTML Player' | translate }}
                    </button>
                </div>
            </div>

            <!-- Method 3: Terminal CLI Command -->
            <div class="border-top pt-3">
                <h5 class="mb-2 guide-title text-info fw-bold">{{ 'Method 3 (Classic): Terminal CLI Command ($ asciinema play)' | translate }}</h5>
                <p class="guide-text small mb-2">
                    {{ 'When recording finishes, the absolute path of the .cast file is copied to clipboard. You can play it anytime in terminal using asciinema play command:' | translate }}
                </p>
                <div class="input-group w-100 mb-2">
                    <span class="input-group-text font-monospace">$</span>
                    <input type="text" class="form-control font-monospace" [value]="'asciinema play &quot;' + savePath + '/filename.cast&quot;'" readonly>
                    <button class="btn btn-outline-secondary" (click)="copyCommand('asciinema play &quot;' + savePath + '/filename.cast&quot;')">{{ 'Copy Command Example' | translate }}</button>
                </div>
                <div class="small guide-tip">
                    {{ 'Note: During asciinema play execution, you can use Space (pause/play), f (2x speed), . (step frame).' | translate }}
                </div>
            </div>
        </div>

        <div class="card p-3 mb-4 guide-card" *ngIf="cliInfo">
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

        <!-- Section 5: Hotkeys & Reference Guide (Bottom Placement) -->
        <h3 class="mt-4 mb-3">{{ 'Hotkeys & Reference Guide' | translate }}</h3>

        <div class="card p-3 mb-4 guide-card">
            <p class="guide-text small mb-3">
                {{ 'Asciinema features can be controlled using 6 hotkeys below. To change or add hotkeys, go to Tabby Settings > Hotkeys and search for Asciinema.' | translate }}
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
                        <td><strong>{{ 'Start / Stop Recording (Toggle)' | translate }}</strong></td>
                        <td><span class="badge bg-primary">Ctrl + Shift + R</span></td>
                        <td>{{ 'Toggles recording state back and forth.' | translate }}</td>
                    </tr>
                    <tr>
                        <td><strong>{{ 'Start Recording Only' | translate }}</strong></td>
                        <td><span class="badge bg-secondary">{{ 'Unassigned (Custom)' | translate }}</span></td>
                        <td>{{ 'Starts recording for the active terminal session.' | translate }}</td>
                    </tr>
                    <tr>
                        <td><strong>{{ 'Stop Recording Only' | translate }}</strong></td>
                        <td><span class="badge bg-secondary">{{ 'Unassigned (Custom)' | translate }}</span></td>
                        <td>{{ 'Stops recording and saves to a .cast file.' | translate }}</td>
                    </tr>
                    <tr>
                        <td><strong>{{ 'Session Discovery & Custom Record' | translate }}</strong></td>
                        <td><span class="badge bg-secondary">{{ 'Unassigned (Custom)' | translate }}</span></td>
                        <td>{{ 'Opens headless target session discovery modal (Docker/Tmux).' | translate }}</td>
                    </tr>
                    <tr>
                        <td><strong>{{ 'Play Last Recording in CLI' | translate }}</strong></td>
                        <td><span class="badge bg-primary">Ctrl + Shift + P</span></td>
                        <td>{{ 'Auto-types asciinema play command into terminal session.' | translate }}</td>
                    </tr>
                    <tr>
                        <td><strong>{{ 'Open Settings & Help' | translate }}</strong></td>
                        <td><span class="badge bg-secondary">{{ 'Unassigned (Custom)' | translate }}</span></td>
                        <td>{{ 'Opens Asciinema settings tab immediately.' | translate }}</td>
                    </tr>
                </tbody>
            </table>
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
            border-bottom: 1px solid var(--bs-border-color, rgba(255, 255, 255, 0.15));
        }
        .sub-option-line {
            background-color: rgba(255, 255, 255, 0.02);
            border-bottom: 1px solid var(--bs-border-color, rgba(255, 255, 255, 0.15));
        }
        .form-line .header {
            flex-grow: 1;
            padding-right: 15px;
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

    get showQuickRecordButton(): boolean {
        return this.config.store.pluginConfig?.['asciinema']?.showQuickRecordButton ?? true
    }

    set showQuickRecordButton(val: boolean) {
        this.updatePluginConfig('showQuickRecordButton', val)
    }

    get showSessionPickerButton(): boolean {
        return this.config.store.pluginConfig?.['asciinema']?.showSessionPickerButton ?? true
    }

    set showSessionPickerButton(val: boolean) {
        this.updatePluginConfig('showSessionPickerButton', val)
    }

    get formatVersion(): string {
        return this.config.store.pluginConfig?.['asciinema']?.formatVersion || 'v2'
    }

    set formatVersion(val: string) {
        this.updatePluginConfig('formatVersion', val)
    }

    get filenamePattern(): string {
        return this.config.store.pluginConfig?.['asciinema']?.filenamePattern || '{date}_{host}'
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

    get maxSingleFileSizeMB(): number {
        const val = Number(this.config.store.pluginConfig?.['asciinema']?.maxSingleFileSizeMB)
        return isNaN(val) || val <= 0 ? 8 : Math.min(val, 30)
    }

    set maxSingleFileSizeMB(val: number) {
        const num = Math.max(1, Math.min(Number(val) || 8, 30))
        this.updatePluginConfig('maxSingleFileSizeMB', num)
    }

    get enableFileSplitting(): boolean {
        const val = this.config.store.pluginConfig?.['asciinema']?.enableFileSplitting
        return val !== undefined ? Boolean(val) : true
    }

    set enableFileSplitting(val: boolean) {
        this.updatePluginConfig('enableFileSplitting', val)
    }

    get maxSplitCount(): number {
        const val = Number(this.config.store.pluginConfig?.['asciinema']?.maxSplitCount)
        return isNaN(val) || val < 0 ? 0 : val
    }

    set maxSplitCount(val: number) {
        const num = Math.max(0, Math.min(Number(val) || 0, 50))
        this.updatePluginConfig('maxSplitCount', num)
    }

    get calculatedMaxParts(): number {
        const total = this.maxStorageMB || 100
        const single = this.maxSingleFileSizeMB || 8
        return Math.max(1, Math.floor(total / single))
    }

    get maxStorageMB(): number {
        const val = Number(this.config.store.pluginConfig?.['asciinema']?.maxStorageMB)
        return isNaN(val) || val <= 0 ? 100 : val
    }

    set maxStorageMB(val: number) {
        const num = Math.max(10, Number(val) || 100)
        this.updatePluginConfig('maxStorageMB', num)
    }

    get savePath(): string {
        return this.config.store.pluginConfig?.['asciinema']?.savePath || path.join(os.homedir(), 'Downloads', 'AsciinemaRecordings')
    }

    set savePath(val: string) {
        this.updatePluginConfig('savePath', val)
    }

    get maskingChar(): string {
        return this.config.store.pluginConfig?.['asciinema']?.maskingChar || '*'
    }

    set maskingChar(val: string) {
        this.updatePluginConfig('maskingChar', val)
    }

    setMaskingChar(char: string): void {
        this.maskingChar = char
        this.saveConfig()
    }

    private updatePluginConfig(key: string, val: any): void {
        if (!this.config.store.pluginConfig) {
            this.config.store.pluginConfig = {}
        }
        if (!this.config.store.pluginConfig['asciinema']) {
            this.config.store.pluginConfig['asciinema'] = {}
        }
        this.config.store.pluginConfig['asciinema'][key] = val
        this.config.save()
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

    private getFilePathFromFile(file: File): string {
        let filePath = (file as any).path
        if (!filePath) {
            try {
                const webUtils = (window as any).require?.('electron')?.webUtils
                if (webUtils && typeof webUtils.getPathForFile === 'function') {
                    filePath = webUtils.getPathForFile(file)
                }
            } catch (e) {}
        }

        if (!filePath || !path.isAbsolute(filePath)) {
            const fileName = file.name || filePath || ''
            if (this.savePath && fileName) {
                const combined = path.join(this.savePath, fileName)
                if (fs.existsSync(combined)) {
                    return combined
                }
            }
        }
        return filePath || file.name
    }

    triggerFileSelectForScan() {
        this.scanFileInput?.nativeElement.click()
    }

    onScanFileSelected(event: Event) {
        const input = event.target as HTMLInputElement
        if (input.files && input.files.length > 0) {
            const file = input.files[0]
            const realPath = this.getFilePathFromFile(file)
            this.performScan(realPath)
        }
    }

    triggerFileSelectForUpload() {
        this.uploadFileInput?.nativeElement.click()
    }

    onUploadFileSelected(event: Event) {
        const input = event.target as HTMLInputElement
        if (input.files && input.files.length > 0) {
            const file = input.files[0]
            this.uploadFilePath = this.getFilePathFromFile(file)
        }
    }

    async uploadSpecifiedFile() {
        const targetPath = this.uploadFilePath
        if (!targetPath || !fs.existsSync(targetPath)) {
            this.notifications.error(this.translate.instant('Upload Failed'), 'File not found: ' + targetPath)
            return
        }

        this.isUploading = true
        let fileToUpload = targetPath
        let tempCreatedPath: string | null = null

        try {
            if (this.uploadTitle && this.uploadTitle.trim()) {
                const lines = fs.readFileSync(targetPath, 'utf8').split('\n')
                if (lines.length > 0 && lines[0].trim()) {
                    try {
                        const header = JSON.parse(lines[0])
                        header.title = this.uploadTitle.trim()
                        lines[0] = JSON.stringify(header)

                        const tempPath = path.join(path.dirname(targetPath), `.upload_temp_${Date.now()}.cast`)
                        fs.writeFileSync(tempPath, lines.join('\n') + '\n', 'utf8')
                        fileToUpload = tempPath
                        tempCreatedPath = tempPath
                    } catch (e) {}
                }
            }

            const url = await this.recorder.uploadToAsciinema(fileToUpload)
            this.platform.setClipboard({ text: url })
            this.notifications.info(
                this.translate.instant('Uploaded to asciinema.org successfully!'),
                `${this.translate.instant('Web URL copied to clipboard:')}\n${url}`,
            )
        } catch (e: any) {
            this.notifications.error(this.translate.instant('Upload Failed'), e.message || String(e))
        } finally {
            if (tempCreatedPath && fs.existsSync(tempCreatedPath)) {
                try { fs.unlinkSync(tempCreatedPath) } catch (e) {}
            }
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
            const maskedContent = maskCastContent(content, selectedKeywords, this.maskingChar)

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

    downloadStandalonePlayer() {
        try {
            const targetDir = this.savePath
            if (!fs.existsSync(targetDir)) {
                fs.mkdirSync(targetDir, { recursive: true })
            }

            const targetFilePath = path.join(targetDir, 'asciinema-player.html')
            fs.writeFileSync(targetFilePath, STANDALONE_PLAYER_HTML, 'utf8')

            this.platform.setClipboard({ text: targetFilePath })
            this.notifications.info(
                this.translate.instant('Standalone HTML Player saved to save folder'),
                targetFilePath,
            )
        } catch (e: any) {
            this.notifications.error(this.translate.instant('Save Failed'), e.message || String(e))
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
