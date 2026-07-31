import { execFile } from 'child_process'
import * as os from 'os'
import * as fs from 'fs'

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

    const envPATH = process.env.PATH || ''
    const extraPaths = '/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:~/.local/bin'
    const fullPATH = `${extraPaths}:${envPATH}`
    const execOptions = { env: { ...process.env, PATH: fullPATH } }

    return new Promise((resolve) => {
        // 1. PATH 환경 변수 기준 1차 탐색
        execFile('asciinema', ['--version'], execOptions, (err, stdout) => {
            if (!err && stdout && stdout.trim()) {
                resolve({
                    installed: true,
                    version: stdout.trim(),
                    guide,
                    url,
                    platformName,
                })
                return
            }

            // 2. macOS Homebrew 및 주요 설치 경로 직접 탐색
            const candidates = [
                '/opt/homebrew/bin/asciinema',
                '/usr/local/bin/asciinema',
                `${os.homedir()}/.local/bin/asciinema`,
                '/usr/bin/asciinema',
            ]

            let checked = 0
            let found = false

            for (const candidate of candidates) {
                if (fs.existsSync(candidate)) {
                    found = true
                    execFile(candidate, ['--version'], (err2, stdout2) => {
                        if (!err2 && stdout2 && stdout2.trim()) {
                            resolve({
                                installed: true,
                                version: stdout2.trim(),
                                guide,
                                url,
                                platformName,
                            })
                        } else {
                            resolve({ installed: false, guide, url, platformName })
                        }
                    })
                    break
                }
            }

            if (!found) {
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

