# Repo-Grundgerüst QSL73 — Implementierungsplan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Lokales + Remote-Repo anlegen, Verzeichnisstruktur und alle Basis-Dateien erstellen, beide Branches pushen.

**Architecture:** Reines Scaffold — kein Anwendungscode. Einzige Versions-Quelle: `src/qsl73/__version__.py`. Alle anderen Stellen (CHANGELOG, README, späteres PyInstaller-Build) referenzieren diese Datei.

**Tech Stack:** Python 3.11, Git/GitHub, PyYAML (Config-Vorlage), MIT-Lizenz, SemVer 0.1.0

---

### Task 1: Verzeichnisstruktur anlegen

**Files:**
- Create: `src/qsl73/__init__.py`
- Create: `src/qsl73/__version__.py`
- Create: `assets/.gitkeep`
- Create: `docs/.gitkeep`

- [ ] Verzeichnisse anlegen: `src/qsl73/`, `assets/`, `docs/`
- [ ] Logo (`qsl73logo.png`) von Repo-Root nach `assets/` verschieben
- [ ] `src/qsl73/__version__.py` schreiben
- [ ] `src/qsl73/__init__.py` schreiben

---

### Task 2: Infrastruktur-Dateien

**Files:**
- Create: `.gitignore`
- Create: `config.example.yaml`
- Create: `README.md`
- Create: `CHANGELOG.md`
- Create: `LICENSE`

- [ ] `.gitignore` (Python + keine Secrets)
- [ ] `config.example.yaml` (alle Felder aus KONZEPT.md §4, Platzhalter)
- [ ] `README.md` (Kurzbeschreibung, Zweck, Inhaber, Lizenz, Status)
- [ ] `CHANGELOG.md` (Keep-a-Changelog, Eintrag 0.1.0)
- [ ] `LICENSE` (MIT, DF1DS)

---

### Task 3: Git-Init + GitHub + Push

- [ ] `git init` im lokalen Verzeichnis
- [ ] GitHub-Repo `kainomatic/qsl73` anlegen (öffentlich)
- [ ] Remote `origin` setzen
- [ ] Initialen Commit auf `dev`
- [ ] Branch `main` von `dev` anlegen
- [ ] Beide Branches pushen
