import { Injectable } from '@angular/core'
import { ToolbarButtonProvider, ToolbarButton, AppService, TranslateService, SplitTabComponent, ConfigService, NotificationsService, PlatformService, HotkeysService } from 'tabby-core'
import { BaseTerminalTabComponent } from 'tabby-terminal'
import { NgbModal } from '@ng-bootstrap/ng-bootstrap'
import { AsciinemaRecorderService } from './services/recorder.service'
import { AsciinemaSessionPickerModalComponent } from './components/sessionPickerModal.component'
import { forwardIcon } from './icons/forwardIcon'
import { registerPluginTranslations } from './i18n'

const iconRecord = require('./icons/record.svg')
const iconStop = require('./icons/stop.svg')

function resolveIcon(iconRaw: any): string {
    return typeof iconRaw === 'string' ? iconRaw : (iconRaw.default || iconRaw)
}

@Injectable()
export class AsciinemaButtonProvider extends ToolbarButtonProvider {
    private quickToolbarButton: ToolbarButton | null = null
    private customToolbarButton: ToolbarButton | null = null

    constructor (
        private app: AppService,
        private recorder: AsciinemaRecorderService,
        private translate: TranslateService,
        private config: ConfigService,
        private notifications: NotificationsService,
        private platform: PlatformService,
        private ngbModal: NgbModal,
        hotkeys: HotkeysService,
    ) {
        super()
        registerPluginTranslations(this.translate)

        hotkeys.hotkey$.subscribe(async (hotkey) => {
            const tab = this.getTerminalTab()
            if (hotkey === 'asciinema-toggle-recording') {
                if (tab) {
                    this.recorder.toggleRecording(tab)
                }
            } else if (hotkey === 'asciinema-start-recording') {
                if (tab) {
                    this.recorder.startRecording(tab)
                }
            } else if (hotkey === 'asciinema-stop-recording') {
                if (tab) {
                    this.recorder.stopRecording(tab)
                }
            } else if (hotkey === 'asciinema-session-picker') {
                if (tab && this.recorder.isRecording(tab)) {
                    this.recorder.stopRecording(tab)
                    this.updateButtonState()
                } else {
                    this.openSessionPickerModal()
                }
            } else if (hotkey === 'asciinema-play-last') {
                this.recorder.playLastRecording(tab)
            } else if (hotkey === 'asciinema-open-settings') {
                this.recorder.openSettings()
            }
        })

        this.recorder.stateChanged$.subscribe(() => this.updateButtonState())
        this.app.activeTabChange$.subscribe(() => this.updateButtonState())
        this.config.changed$.subscribe(() => this.updateButtonState())
        this.translate.onLangChange.subscribe(() => this.updateButtonState())
    }

    private getIcon (isRecording: boolean): string {
        return resolveIcon(isRecording ? iconStop : iconRecord)
    }

    private getTerminalTab (tab: any = this.app.activeTab): BaseTerminalTabComponent<any> | null {
        if (!tab) {
            return null
        }
        if (tab instanceof BaseTerminalTabComponent) {
            return tab
        }
        if (tab instanceof SplitTabComponent) {
            const focused = tab.getFocusedTab()
            const found = this.getTerminalTab(focused)
            if (found) {
                return found
            }
            for (const child of tab.getAllTabs()) {
                const f = this.getTerminalTab(child)
                if (f) {
                    return f
                }
            }
        }
        return null
    }

    private updateButtonState (): void {
        const tab = this.getTerminalTab()
        const isRecording = !!(tab && this.recorder.isRecording(tab))

        if (this.quickToolbarButton) {
            this.quickToolbarButton.icon = this.getIcon(isRecording)
            this.quickToolbarButton.title = isRecording
                ? this.translate.instant('Asciinema Stop Recording (Ctrl+Shift+R)')
                : this.translate.instant('Asciinema Quick Record (Ctrl+Shift+R)')
        }
    }

    private openSessionPickerModal(): void {
        const activeTab = this.getTerminalTab()
        const modalRef = this.ngbModal.open(AsciinemaSessionPickerModalComponent, {
            size: 'md',
            backdrop: 'static',
        })

        modalRef.componentInstance.activeTab = activeTab

        modalRef.result.then((res) => {
            if (res) {
                const tab = this.getTerminalTab()
                if (tab && (tab as any).session) {
                    this.recorder.startRecording(tab, res.sessionPrefix, {
                        customFileLimitMB: res.customFileLimitMB,
                        customMaxSplits: res.customMaxSplits,
                    })

                    if (res.innerCommand && res.innerCommand.trim()) {
                        ;(tab as any).session.write(res.innerCommand.trim() + '\r')
                    }

                    if (res.timerMinutes && res.timerMinutes > 0) {
                        const ms = res.timerMinutes * 60 * 1000
                        setTimeout(() => {
                            if (this.recorder.isRecording(tab)) {
                                this.recorder.stopRecording(tab)
                                this.notifications.notice(this.translate.instant('Recording stopped by timer limit.'))
                            }
                        }, ms)
                    }

                    this.updateButtonState()
                } else {
                    this.notifications.notice(this.translate.instant('No active terminal session.'))
                }
            }
        }).catch(() => {})
    }

    provide (): ToolbarButton[] {
        const tab = this.getTerminalTab()
        const isRecording = !!(tab && this.recorder.isRecording(tab))
        const buttons: ToolbarButton[] = []

        const showQuick = this.config.store.pluginConfig?.['asciinema']?.showQuickRecordButton ?? true
        const showCustom = this.config.store.pluginConfig?.['asciinema']?.showSessionPickerButton ?? true

        // Button 1: Original Quick Record Button (Single Triangle ▶: record.svg / stop.svg)
        if (showQuick) {
            const quickButton: ToolbarButton = {
                icon: this.getIcon(isRecording),
                title: isRecording 
                    ? this.translate.instant('Asciinema Stop Recording (Ctrl+Shift+R)') 
                    : this.translate.instant('Asciinema Quick Record (Ctrl+Shift+R)'),
                touchBarNSImage: 'NSTouchBarRecordStartTemplate',
                weight: 5,
                click: () => {
                    const currentTab = this.getTerminalTab()
                    if (!currentTab) {
                        return
                    }
                    this.recorder.toggleRecording(currentTab)
                    this.updateButtonState()
                },
            }
            this.quickToolbarButton = quickButton
            buttons.push(quickButton)
        } else {
            this.quickToolbarButton = null
        }

        // Button 2: Twin Triangle Forward Icon (▶▶: forwardIcon) for Session Discovery & Custom Record
        if (showCustom) {
            const customButton: ToolbarButton = {
                icon: forwardIcon,
                title: this.translate.instant('Asciinema Session & Custom Record'),
                touchBarNSImage: 'NSTouchBarQuickLookTemplate',
                weight: 6,
                click: () => {
                    const currentTab = this.getTerminalTab()
                    if (currentTab && this.recorder.isRecording(currentTab)) {
                        // Stop recording if active
                        this.recorder.stopRecording(currentTab)
                        this.updateButtonState()
                    } else {
                        // Open session picker modal if not recording
                        this.openSessionPickerModal()
                    }
                },
            }
            this.customToolbarButton = customButton
            buttons.push(customButton)
        } else {
            this.customToolbarButton = null
        }

        return buttons
    }
}
