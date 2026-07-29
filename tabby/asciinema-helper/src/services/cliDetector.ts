import { execFile } from 'child_process'
import * as os from 'os'

export interface CLIInfo {
    installed: boolean
    version?: string
    guide: string
    url: string
    platformName: string
}

export function detectAsciinemaCLI (): Promise<CLIInfo> {
    const platform = os.platform()
    let platformName = 'macOS'
    let guide = 'brew install asciinema'
    const url = 'https://asciinema.org'

    if (platform === 'darwin') {
        platformName = 'macOS'
        guide = 'brew install asciinema'
    } else if (platform === 'linux') {
        platformName = 'Linux'
        guide = 'sudo apt install asciinema (또는 pip install asciinema)'
    } else if (platform === 'win32') {
        platformName = 'Windows'
        guide = 'pip install asciinema (또는 WSL 환경 설치)'
    } else {
        platformName = platform
        guide = 'pip install asciinema'
    }

    return new Promise((resolve) => {
        execFile('asciinema', ['--version'], (err, stdout) => {
            if (!err && stdout && stdout.trim()) {
                resolve({
                    installed: true,
                    version: stdout.trim(),
                    guide,
                    url,
                    platformName,
                })
            } else {
                resolve({
                    installed: false,
                    guide,
                    url,
                    platformName,
                })
            }
        })
    })
}
