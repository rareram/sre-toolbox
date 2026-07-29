import { Injectable } from '@angular/core'
import { ToolbarButtonProvider, ToolbarButton, AppService, TranslateService, SplitTabComponent, ConfigService, NotificationsService, PlatformService, HotkeysService } from 'tabby-core'
import { BaseTerminalTabComponent } from 'tabby-terminal'
import { AsciinemaRecorderService } from './services/recorder.service'
import { registerPluginTranslations } from './i18n'

const iconRecord = require('./icons/record.svg')
const iconStop = require('./icons/stop.svg')

function resolveIcon(iconRaw: any): string {
    return typeof iconRaw === 'string' ? iconRaw : (iconRaw.default || iconRaw)
}

@Injectable()
export class AsciinemaButtonProvider extends ToolbarButtonProvider {
    private activeToolbarButton: ToolbarButton | null = null

    constructor (
        private app: AppService,
        private recorder: AsciinemaRecorderService,
        private translate: TranslateService,
        private config: ConfigService,
        private notifications: NotificationsService,
        private platform: PlatformService,
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
        if (!this.activeToolbarButton) {
            return
        }
        const tab = this.getTerminalTab()
        const isRecording = !!(tab && this.recorder.isRecording(tab))

        this.activeToolbarButton.icon = this.getIcon(isRecording)
        this.activeToolbarButton.title = isRecording
            ? this.translate.instant('Asciinema Stop Recording (Ctrl+Shift+R)')
            : this.translate.instant('Asciinema Start Recording (Ctrl+Shift+R)')
    }

    provide (): ToolbarButton[] {
        const tab = this.getTerminalTab()
        const isRecording = !!(tab && this.recorder.isRecording(tab))

        const button: ToolbarButton = {
            icon: this.getIcon(isRecording),
            title: isRecording 
                ? this.translate.instant('Asciinema Stop Recording (Ctrl+Shift+R)') 
                : this.translate.instant('Asciinema Start Recording (Ctrl+Shift+R)'),
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

        this.activeToolbarButton = button
        return [button]
    }
}
