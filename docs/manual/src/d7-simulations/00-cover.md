---
title: "ChainSentinel — Simulation & Demo Guide"
subtitle: "Document D7 of the ChainSentinel Manual"
author: "ChainSentinel Engineering"
date: "2026-05-12"
version: "1.0"
---

# About this document

The five Foundry simulations that ship with ChainSentinel are the
canonical end-to-end demos. Each scenario reproduces a real-world attack
class against a *victim* protocol and provides:

- Solidity sources for the victim, the attacker, and ambient activity.
- Foundry scripts that deploy and execute the scenario phase-by-phase.
- A `client/` directory containing the ABIs and manifest that
  ChainSentinel would receive from a real client.

This document walks through each scenario, lists the contracts and
scripts, and notes which signals and patterns each is expected to fire.

![Simulation scenario matrix](../../diagrams/rendered/13-scenario-matrix.png)
