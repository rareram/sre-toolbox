# tabby-asciinema-helper

> Asciinema terminal session recorder helper plugin for [Tabby](https://tabby.sh)

[![npm version](https://img.shields.io/npm/v/tabby-asciinema-helper.svg)](https://www.npmjs.com/package/tabby-asciinema-helper)
[![license](https://img.shields.io/npm/l/tabby-asciinema-helper.svg)](https://github.com/rareram/sre-toolbox/blob/main/LICENSE)

A plugin for Tabby that records terminal sessions into standard **asciinema `.cast` (v2 standard / v3 experimental)** files, supports ANSI-preserving sensitive data masking, and enables direct uploads to asciinema.org.

---

## Key Features

* **Session Recording**: Record terminal sessions directly using toolbar buttons or hotkeys.
* **No Remote Server Setup**: Captures output directly inside Tabby. No need to install `asciinema` on remote SSH servers.
* **Standard `.cast` Format**: Compatible with standard `asciinema` CLI and web players (v2 standard recommended).
* **Sensitive Data Masking**: Interactively scans IPs, User IDs, FQDN domains/hosts, passwords, and API tokens. Preserves ANSI color codes and 1:1 terminal display width using custom mask characters (`*`, `█`, `▒`).
* **asciinema.org Upload**: Upload `.cast` files to asciinema.org with custom titles and copy web URLs to the clipboard.
* **Filename Templates**: Customizable filename patterns (`{host}`, `{date}`, `{prefix}`) with automatic numbering to prevent overwriting existing files.
* **Auto Clipboard Copy**: Automatically copies saved `.cast` file paths to the clipboard upon stopping recording.
* **Language Support**: Displays English or Korean based on Tabby settings and OS language.
* **5 Configurable Hotkeys**:
  * `Start / Stop Recording (Toggle)` (Default: `Ctrl+Shift+R`)
  * `Start Recording`
  * `Stop Recording`
  * `Play Last Recording in CLI` (Default: `Ctrl+Shift+P`)
  * `Open Settings & Help`

---

## Security & Privacy Note

> **Note**: Recording captures terminal text streams into `.cast` files. Before sharing recordings, use **Sensitive Data Masking** in Tabby Settings to redact passwords, tokens, or IP addresses.

---

## Installation

### Option 1: Install via Tabby Settings (Recommended)
1. Open **Tabby Settings** -> **Plugins**.
2. Search for `tabby-asciinema-helper`.
3. Click **Install**.
4. Restart Tabby.

### Option 2: Manual / Local Installation
```bash
git clone https://github.com/rareram/sre-toolbox.git
cd sre-toolbox/tabby/asciinema-helper

npm install --legacy-peer-deps
npm run build
```

---

## How to Use

1. Open any terminal tab in Tabby.
2. Click the **Asciinema Start Recording** button (or press `Ctrl+Shift+R`).
3. Run your commands in the terminal.
4. Click **Asciinema Stop Recording** (or press `Ctrl+Shift+R`).
5. The `.cast` file path is saved to `Downloads/AsciinemaRecordings` and copied to your clipboard.
6. Open **Tabby Settings > Asciinema** to mask sensitive data or upload to `asciinema.org`.

---

## 개요

### 주요 기능
* Tabby 터미널 프로그램에서 asciinema 를 활용하기 쉽도록 도와주는 플러그인입니다.
* **터미널 화면 녹화**: 툴바 버튼과 단축키로 작업 내용을 `.cast` 파일로 녹화합니다.
* **원격 서버 설치 불필요**: 원격 서버에 프로그램을 깔 필요 없이 Tabby 프로그램 자체에서 바로 녹화합니다.
* **민감정보 마스킹**: IP, 계정 ID, FQDN 도메인/호스트명, 비밀번호, API 토큰을 정밀 스캔하고, ANSI 색상 코드를 100% 보존하며 1:1 터미널 디스플레이 셀 폭에 맞춰 치환 문자(`*`, `█`, `▒` 등)로 안전하게 마스킹한 복사본을 생성합니다.
* **asciinema.org 업로드**: 녹화 파일을 웹으로 올려 공유 링크를 클립보드로 복사합니다.
* **파일명 패턴 & 중복 방지**: 날짜/호스트명 기반 파일명 설정 및 중복 시 번호(`_1.cast`) 자동 부여.
* **다국어 지원**: Tabby 및 OS 설정 언어에 따라 한국어/영어로 표시됩니다.
* **5가지 단축키**: 녹화 토글(`Ctrl+Shift+R`), CLI 즉시 재생(`Ctrl+Shift+P`) 등 제공.

---

## License

[MIT License](https://github.com/rareram/sre-toolbox/blob/main/LICENSE) © [YangHeeJong](https://github.com/rareram/sre-toolbox)
