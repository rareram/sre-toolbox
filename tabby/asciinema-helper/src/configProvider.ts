import { Injectable } from '@angular/core'
import { ConfigProvider } from 'tabby-core'

@Injectable()
export class AsciinemaConfigProvider extends ConfigProvider {
    defaults = {
        hotkeys: {
            'asciinema-toggle-recording': ['Ctrl-Shift-R'],
            'asciinema-start-recording': [],
            'asciinema-stop-recording': [],
            'asciinema-play-last': ['Ctrl-Shift-P'],
            'asciinema-open-settings': [],
        },
        pluginConfig: {
            asciinema: {
                formatVersion: 'v2',
                filePrefix: 'asciinema',
                filenamePattern: '{host}_{date}',
                idleTimeLimit: 0,
                maskingKeywords: '',
                maskingChar: '*',
                savePath: '',
            },
        },
    }
}
