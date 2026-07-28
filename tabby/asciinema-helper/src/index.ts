import { NgModule } from '@angular/core'
import { CommonModule } from '@angular/common'
import { FormsModule } from '@angular/forms'
import TabbyCoreModule, { ToolbarButtonProvider, HotkeyProvider, ConfigProvider } from 'tabby-core'
import TabbyTerminalModule from 'tabby-terminal'
import TabbySettingsModule, { SettingsTabProvider } from 'tabby-settings'

import { AsciinemaRecorderService } from './services/recorder.service'
import { AsciinemaButtonProvider } from './buttonProvider'
import { AsciinemaHotkeyProvider } from './hotkeyProvider'
import { AsciinemaConfigProvider } from './configProvider'
import { AsciinemaSettingsTabProvider } from './settingsTabProvider'
import { AsciinemaSettingsTabComponent } from './components/settingsTab.component'

@NgModule({
    imports: [
        CommonModule,
        FormsModule,
        TabbyCoreModule,
        TabbyTerminalModule,
        TabbySettingsModule,
    ],
    providers: [
        AsciinemaRecorderService,
        { provide: ToolbarButtonProvider, useClass: AsciinemaButtonProvider, multi: true },
        { provide: SettingsTabProvider, useClass: AsciinemaSettingsTabProvider, multi: true },
        { provide: HotkeyProvider, useClass: AsciinemaHotkeyProvider, multi: true },
        { provide: ConfigProvider, useClass: AsciinemaConfigProvider, multi: true },
    ],
    declarations: [
        AsciinemaSettingsTabComponent,
    ],
})
export default class AsciinemaModule { }
