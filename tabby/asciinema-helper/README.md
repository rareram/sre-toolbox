# Tabby Asciinema Helper Plugin

Tabby Asciinema Helper is a native session recorder plugin for Tabby Terminal. It captures active terminal sessions as well as **Headless Target Sessions**—such as background Docker container logs (`docker logs -f`), detached Tmux sessions (`tmux attach -t`), and Herdr Multi-Agent sessions (`herdr session attach`)—into standard `.cast` format files without screen clutter.

---

## Screenshots

<p align="left">
  <img src="https://raw.githubusercontent.com/rareram/sre-toolbox/main/docs/asciinema-helper/asciinema_1.png" alt="Session Discovery & Custom Record Modal" width="40%" />
  <img src="https://raw.githubusercontent.com/rareram/sre-toolbox/main/docs/asciinema-helper/asciinema_2.png" alt="Plugin Settings & Sensitive Redaction Tool" width="40%" />
</p>

---

## Key Features

### English
* **Headless Target Session Recording**: Discover and attach directly to background process streams (Docker logs, Tmux, Herdr multi-agent panes) without occupying or polluting your active terminal screen.
* **Direct .cast File Generation**: No external `asciinema` CLI binary is required for recording. Uses Tabby's internal terminal output streams for direct `.cast` file generation.
* **Sensitive Data Redaction**: Interactive scanning and masking of IP addresses, API tokens, and credentials preserving 1:1 terminal display width.
* **Storage & File Limits**: Supports ISO-8601 chronological file naming (`{date}_{host}`), single file size limits (default 8 MB), automatic file splitting, and storage capacity auto-cleanup (default 100 MB).
* **Standalone HTML Player**: Generates self-contained HTML files ([`docs/asciinema-helper/asciinema-player.html`](https://github.com/rareram/sre-toolbox/blob/main/docs/asciinema-helper/asciinema-player.html)) for viewing `.cast` recordings in any web browser when CLI is not installed.

### Korean
* **Headless 백그라운드 세션 녹화**: 화면 뷰포트를 오염시키지 않고 백그라운드 Docker 컨테이너 로그, Tmux 세션, Herdr 멀티에이전트 페인 스트림에 직접 어태치하여 녹화.
* **.cast 포맷 자체 생성**: 녹화를 위한 별도의 `asciinema` CLI 설치 불필요. Tabby 내부 터미널 입출력 스트림을 통해 `.cast` 포맷 파일 직접 생성.
* **민감정보 마스킹**: IP 주소, API 토큰, 비밀번호 등을 정규식으로 감지하고 1:1 터미널 표시 너비를 보존하여 마스킹.
* **용량 및 파일 저장 제어**: ISO-8601 날짜 우선 정렬(`{date}_{host}`), 단일 파일 용량 제한(기본 8 MB), 자동 파일 분할 및 저장소 자동 정돈(기본 100 MB).
* **단독 실행형 HTML 플레이어**: CLI 미설치 환경에서도 웹 브라우저에서 `.cast` 녹화본을 바로 감상할 수 있는 단독 실행형 HTML 플레이어([`docs/asciinema-helper/asciinema-player.html`](https://github.com/rareram/sre-toolbox/blob/main/docs/asciinema-helper/asciinema-player.html)) 파일 제공.

---

## Quick Start Guide

### 1. Quick Terminal Recording (`Ctrl+Shift+R`)
* Press `Ctrl+Shift+R` or click the **Record Button** on the top toolbar to toggle recording for the active terminal tab.
* Upon stopping, the absolute file path of the `.cast` recording is automatically copied to your clipboard.

### 2. Headless Session Discovery & Custom Recording
* Click the **Session Discovery Button** (Twin Triangle icon) on the toolbar.
* Select the target headless process type: **Docker Container**, **Tmux Session**, or **Herdr Session**.
* The plugin scans active background sessions without executing disruptive terminal commands.
* Set optional one-off parameters (e.g. recording timer limit, custom file size limit) before attaching.

---

## Hotkeys Reference

| Action | Default Hotkey | Description |
| :--- | :--- | :--- |
| **Start / Stop Recording** | `Ctrl+Shift+R` | Toggle recording for the active terminal session |
| **Play Last Recording** | `Ctrl+Shift+P` | Execute `asciinema play` in active terminal |
| **Start Recording Only** | *Unassigned* | Explicit start recording command |
| **Stop Recording Only** | *Unassigned* | Explicit stop recording command |
| **Open Settings & Help** | *Unassigned* | Open Asciinema plugin settings tab |

---

## Configuration Options

Access configuration via `Tabby Settings` > `Plugins` > `Asciinema`:

* **Filename Pattern**: Default `{date}_{host}` (Supported variables: `{date}`, `{host}`, `{prefix}`, `{title}`).
* **Single File Limit**: Default `8 MB` (Maximum `30 MB`).
* **Auto-Split Files**: Automatically splits recordings into consecutive files (`_2.cast`, `_3.cast`) when size limit is reached.
* **Storage Limit**: Default `100 MB` total directory capacity (removes oldest files when full).
* **Sensitive Keywords**: Comma-separated list for automatic masking (e.g. `password,token,secret`).

---

## License

MIT License © rareram
