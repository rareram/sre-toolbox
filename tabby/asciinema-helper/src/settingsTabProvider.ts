import { Injectable } from '@angular/core'
import { SettingsTabProvider } from 'tabby-settings'
import { TranslateService } from 'tabby-core'
import { AsciinemaSettingsTabComponent } from './components/settingsTab.component'
import { registerPluginTranslations } from './i18n'

@Injectable()
export class AsciinemaSettingsTabProvider extends SettingsTabProvider {
    id = 'asciinema'
    icon = 'video'
    title = ''
    weight = 10

    constructor (private translate: TranslateService) {
        super()
        registerPluginTranslations(this.translate)
        this.title = this.translate.instant('Asciinema Recording')
        this.translate.onLangChange.subscribe(() => {
            this.title = this.translate.instant('Asciinema Recording')
        })
    }

    getComponentType (): any {
        return AsciinemaSettingsTabComponent
    }
}
