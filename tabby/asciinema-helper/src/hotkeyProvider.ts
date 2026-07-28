import { Injectable } from '@angular/core'
import { HotkeyProvider, HotkeyDescription, TranslateService } from 'tabby-core'
import { registerPluginTranslations } from './i18n'

@Injectable()
export class AsciinemaHotkeyProvider extends HotkeyProvider {
    constructor (private translate: TranslateService) {
        super()
        registerPluginTranslations(this.translate)
    }

    async provide (): Promise<HotkeyDescription[]> {
        return [
            {
                id: 'asciinema-toggle-recording',
                name: this.translate.instant('Asciinema: Start / Stop Recording (Toggle)'),
            },
            {
                id: 'asciinema-start-recording',
                name: this.translate.instant('Asciinema: Start Recording'),
            },
            {
                id: 'asciinema-stop-recording',
                name: this.translate.instant('Asciinema: Stop Recording'),
            },
            {
                id: 'asciinema-play-last',
                name: this.translate.instant('Asciinema: Play Last Recording (CLI)'),
            },
            {
                id: 'asciinema-open-settings',
                name: this.translate.instant('Asciinema: Open Settings & Help'),
            },
        ]
    }
}
