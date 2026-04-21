# Server+ Exam Prep

Desktop CompTIA Server+ study app built with Electron. It supports two workflows:

- Practice mode: browse the full extracted bank, answer immediately, and review explanations.
- Exam simulator: generate a random timed exam using the official CompTIA Server+ SK0-005 profile of up to 90 questions in 90 minutes.

## Download

| Package | Link |
|---------|------|
| Portable app | [Download ServerPlusExamPrep-Portable.exe](https://github.com/albertje8118/server-plus-exam-prep/releases/latest/download/ServerPlusExamPrep-Portable.exe) |
| Installer | [Download ServerPlusExamPrep-Setup.exe](https://github.com/albertje8118/server-plus-exam-prep/releases/latest/download/ServerPlusExamPrep-Setup.exe) |

End users do not need Node.js, Python, SQLite, or any other prerequisite. Both the portable build and the NSIS installer bundle the Electron runtime, the SQLite database, and extracted question images.

## Install

1. Open the latest GitHub Release.
2. Choose one package:
3. `ServerPlusExamPrep-Portable.exe` to run without installing.
4. `ServerPlusExamPrep-Setup.exe` to install with the NSIS wizard.
5. Launch `Server+ Exam Prep`.

## Features

- Practice mode with instant answer checking and explanations.
- Timed exam simulator with random question selection, review flags, and hidden answers until submission.
- Support for image-based questions, options, and explanation assets.
- Local bundled SQLite-backed question bank with no online dependency.

## Official Exam Target

CompTIA Server+ SK0-005 exam details from CompTIA:

- Exam series code: `SK0-005`
- Number of questions: maximum of `90`
- Length of test: `90 minutes`

Source: https://www.comptia.org/certifications/server

## Development

```bash
npm install
npm start
```

## Build Windows Installer

```bash
npm run build:win
```

Output is written to `dist/` and includes:

- `ServerPlusExamPrep-Portable.exe`
- `ServerPlusExamPrep-Setup.exe`

## GitHub Actions

The workflow in `.github/workflows/build-release.yml` builds both Windows packages on GitHub Actions and publishes stable asset names to GitHub Releases, so the `releases/latest/download/...` links always point to the newest build.