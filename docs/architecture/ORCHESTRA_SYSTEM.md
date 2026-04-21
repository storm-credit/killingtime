# Killing Time Orchestra System

## Goal

Build a configurable subtitle translation pipeline for long-form video, starting with Chinese drama intake and ending with exportable Korean and Spanish subtitle packages.

## What The Orchestra Owns

- task intake and scope locking
- stage routing
- fixed versus dynamic worker activation
- go/no-go judgment at gates
- final package approval

The orchestra does not do every task itself. It decides who should act, in what order, and whether the result is good enough to advance.

## Fixed Core

The following capabilities are always present:

- orchestration
- harness governance
- subtitle discovery
- ASR transcription
- OCR fallback
- translation
- localization QA
- packaging
- web presentation

## Extendable Surface

The following are meant to grow over time:

- dynamic agents
- skill packs
- hooks for automation
- MCP connectors
- market-specific export rules

## Why This Differs From Odd Engine

`Odd Engine` was a music-video production harness.

`Killing Time` keeps the same orchestration philosophy, but its pipeline is media localization first:

- subtitle retrieval before transcription
- OCR fallback before manual rescue
- translation memory and term locking
- subtitle timing and readability QA
- export packaging by market and platform
- no default composition or branded video rendering layer
