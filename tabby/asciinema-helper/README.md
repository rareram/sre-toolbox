# tabby-asciinema-helper

> Asciinema terminal session recorder helper plugin for [Tabby](https://tabby.sh)

[![npm version](https://img.shields.io/npm/v/tabby-asciinema-helper.svg)](https://www.npmjs.com/package/tabby-asciinema-helper)
[![GitHub](https://img.shields.io/badge/GitHub-rareram%2Fsre--toolbox-blue.svg)](https://github.com/rareram/sre-toolbox/tree/main/tabby/asciinema-helper)
[![license](https://img.shields.io/badge/license-MIT-green.svg)](https://github.com/rareram/sre-toolbox/blob/main/LICENSE)

`tabby-asciinema-helper` is a lightweight, zero-server-dependency plugin for Tabby that records terminal sessions directly into standard **asciinema `.cast` (v2)** format.

---

## Features

* **1-Click Recording**: Start and stop recording terminal sessions right from the top toolbar button.
* **No Server Setup Required**: Captures terminal output streams directly inside Tabby's renderer process. No need to install `asciinema` on remote SSH servers.
* **Standard `.cast` (v2) Format**: Fully compatible with `asciinema` CLI player and web players (`asciinema-player`).
* **Auto Clipboard Copy**: Automatically copies the saved `.cast` file path to your clipboard upon stopping recording.
* **Built-in i18n Support**: Automatically switches UI language (English / Korean) based on your Tabby language settings.
* **Custom Toolbar Icon Themes**: Choose between `Classic Red`, `Neon Cyber`, and `Retro Camera` themes with live icon previews.
* **5 Configurable Hotkeys**:
  * `Asciinema: Start / Stop Recording (Toggle)` (Default: `Ctrl+Shift+R`)
  * `Asciinema: Start Recording`
  * `Asciinema: Stop Recording`
  * `Asciinema: Play Last Recording (CLI)` (Default: `Ctrl+Shift+P`)
  * `Asciinema: Open Settings & Help`

---

## Security & Privacy Note

> **Important**: Recording captures all terminal stdout/stdin streams into standard `.cast` (v2) text files. Please ensure you do **not** type or print sensitive credentials (such as passwords, private keys, or API tokens) while a recording session is active.

---

## Installation

### Option 1: Install via Tabby Settings (Recommended)
1. Open **Tabby Settings** -> **Plugins**.
2. Search for `asciinema-helper` or `tabby-asciinema-helper`.
3. Click **Install**.
4. Restart Tabby.

### Option 2: Manual / Local Installation
```bash
# Clone repository
git clone https://github.com/rareram/sre-toolbox.git
cd sre-toolbox/tabby/asciinema-helper

# Install dependencies and build
npm install --legacy-peer-deps
npm run build

# Deploy to Tabby plugins directory
# macOS:
mkdir -p "$HOME/Library/Application Support/tabby/plugins/node_modules/tabby-asciinema-helper"
cp -r dist package.json README.md "$HOME/Library/Application Support/tabby/plugins/node_modules/tabby-asciinema-helper/"

# Linux:
# mkdir -p "$HOME/.config/tabby/plugins/node_modules/tabby-asciinema-helper"

# Windows:
# %APPDATA%\tabby\plugins\node_modules\tabby-asciinema-helper
```

---

## How to Use

1. Open any terminal tab (Local Shell, SSH, Serial, etc.) in Tabby.
2. Click the **Asciinema Start Recording** button on the top toolbar (or press `Ctrl+Shift+R`).
3. Run your commands in the terminal.
4. Click **Asciinema Stop Recording** (or press `Ctrl+Shift+R`).
5. The `.cast` file path will be saved to your `Downloads/AsciinemaRecordings` directory and copied to your clipboard.
6. To play the recording in terminal, press `Ctrl+Shift+P` or run:
   ```bash
   asciinema play "/path/to/recording.cast"
   ```

---

## 한국어 안내 (Korean Overview)

### 주요 특징
* **1-클릭 세션 녹화**: 상단 툴바 버튼 및 단축키로 즉시 터미널 세션을 `.cast` (v2) 파일로 녹화합니다.
* **원격 서버 설치 불필요**: SSH 원격 서버에 `asciinema`를 설치할 필요 없이 Tabby 렌더러 단에서 세션 스트림을 직접 캡처합니다.
* **완벽한 다국어(i18n) 지원**: Tabby 언어 설정에 맞춰 영어/한국어가 자동으로 동기화됩니다.
* **아이콘 테마 미리보기 지원**: 클래식 레드, 네온 사이버, 레트로 카메라 아이콘 테마를 제공합니다.
* **5가지 맞춤 단축키**:
  * 녹화 토글 (`Ctrl+Shift+R`)
  * 최근 녹화본 CLI 즉시 재생 (`Ctrl+Shift+P`)
  * 녹화 전용 시작 / 중지 / 설정 열기

### 보안 및 민감 정보 주의사항
> **주의**: 세션 녹화 기능은 터미널 화면의 모든 입출력 텍스트를 평문(`.cast` 형식)으로 파일에 저장합니다. 녹화 진행 중 비밀번호, SSH 키, API 토큰 등 민감한 인증 정보가 화면에 노출되거나 파일에 기록되지 않도록 주의하십시오.

---

## License

[MIT License](https://github.com/rareram/sre-toolbox/blob/main/LICENSE) © [YangHeeJong](https://github.com/rareram/sre-toolbox)
