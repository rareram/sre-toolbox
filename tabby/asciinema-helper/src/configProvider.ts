import { Injectable } from '@angular/core'
import { ConfigProvider } from 'tabby-core'

@Injectable()
export class AsciinemaConfigProvider extends ConfigProvider {
    defaults = {
        hotkeys: {
            'asciinema-toggle-recording': ['Ctrl-Shift-R'],
            'asciinema-start-recording': [],
            'asciinema-stop-recording': [],
            'asciinema-session-picker': [],
            'asciinema-play-last': ['Ctrl-Shift-P'],
            'asciinema-open-settings': [],
        },
        pluginConfig: {
            asciinema: {
                showQuickRecordButton: true,
                showSessionPickerButton: true,
                formatVersion: 'v2',
                filePrefix: 'asciinema',
                filenamePattern: '{host}_{date}',
                idleTimeLimit: 2.0,
                maxSingleFileSizeMB: 8,
                enableFileSplitting: true,
                maxSplitCount: 0,
                maxStorageMB: 100,
                maskingKeywords: '',
                maskingChar: '*',
                savePath: '',
            },
        },
    }
}
