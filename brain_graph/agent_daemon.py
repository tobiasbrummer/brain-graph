#!/usr/bin/env python3
"""
Agent Daemon: Schedules and runs background agents.
"""
import sys
import time
import schedule
from pathlib import Path

from brain_graph.agents.dreamer import DreamerAgent
from brain_graph.agents.researcher import ResearcherAgent
from brain_graph.agents.gardener import GardenerAgent
from brain_graph.agents.reflex import ReflexEngine
from brain_graph.utils.file_utils import load_config


def run_dreamer(config):
    print("Running Dreamer...", file=sys.stderr)
    try:
        agent = DreamerAgent(Path(".brain_graph/brain.duckdb"), config)
        agent.run()
    except Exception as e:
        print(f"Dreamer failed: {e}", file=sys.stderr)


def run_researcher(config):
    print("Running Researcher...", file=sys.stderr)
    try:
        agent = ResearcherAgent(config)
        agent.run()
    except Exception as e:
        print(f"Researcher failed: {e}", file=sys.stderr)


def run_gardener(config):
    print("Running Gardener...", file=sys.stderr)
    try:
        agent = GardenerAgent(Path(".brain_graph/brain.duckdb"), config)
        agent.run()
    except Exception as e:
        print(f"Gardener failed: {e}", file=sys.stderr)


def run_reflex(config):
    # Reflexes should be fast and frequent
    try:
        engine = ReflexEngine(Path("."))
        engine.run()
    except Exception as e:
        print(f"Reflex failed: {e}", file=sys.stderr)


def main():
    print("Starting Agent Daemon...", file=sys.stderr)
    config = load_config()

    # Schedule jobs based on config
    # Dreamer
    if config.get("agents_dreamer_schedule") == "daily_0300":
        schedule.every().day.at("03:00").do(run_dreamer, config)
    else:
        # Default fallback
        schedule.every().day.at("03:00").do(run_dreamer, config)

    # Researcher
    if config.get("agents_researcher_schedule") == "every_10_minutes":
        schedule.every(10).minutes.do(run_researcher, config)
    else:
        schedule.every(10).minutes.do(run_researcher, config)

    # Gardener
    if config.get("agents_gardener_schedule") == "weekly_monday_0400":
        schedule.every().monday.at("04:00").do(run_gardener, config)
    else:
        schedule.every().monday.at("04:00").do(run_gardener, config)

    # Reflexes (Tools)
    # Run frequently (e.g. every minute)
    schedule.every(1).minutes.do(run_reflex, config)

    # Archivist (New)
    if config.get("agents_archivist_schedule") == "daily_0200":
        # schedule.every().day.at("02:00").do(run_archivist, config)
        pass

    print("Scheduler running. Press Ctrl+C to exit.", file=sys.stderr)

    while True:
        schedule.run_pending()
        time.sleep(60)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Daemon stopped.", file=sys.stderr)
